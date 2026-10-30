"""Data Ark v1.4 manifest loading and static dashboard rendering.

No content downloads, scheduled updates, or executable launches occur here.
Only explicitly configured artwork can be fetched during a build.
"""
import base64
from datetime import datetime
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import warnings

from PIL import Image
import yaml
from app.services.upstream import read_state, read_batch, asset_state

MAX_IMAGE = 5 * 1024 * 1024
POLICIES = {'manual', 'auto', 'pin_version', 'on_network_available'}
FORMATS = {'PNG': ('png', 'image/png'), 'JPEG': ('jpg', 'image/jpeg'),
           'GIF': ('gif', 'image/gif'), 'WEBP': ('webp', 'image/webp')}

class ManifestError(ValueError):
    pass

class UniqueLoader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
    pass

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ManifestError('Manifest keys must be unique strings.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f'{label} must be a nonempty string.')
    return value

def relative_path(value, label):
    text(value, label)
    if '\\' in value or value.startswith('/') or re.match(r'^[A-Za-z]:', value):
        raise ManifestError(f'{label} must be a relative path using forward slashes.')
    if any(part in ('..', '') for part in value.rstrip('/').split('/')):
        raise ManifestError(f'{label} cannot contain traversal or empty path components.')
    return value

def inside(root, value):
    relative_path(value, 'Path')
    root = Path(root).resolve()
    result = (root / value).resolve()
    if not result.is_relative_to(root):
        raise ManifestError('Path resolves outside its permitted root.')
    return result

def url(value, label='URL', local=True):
    text(value, label)
    if any(ord(c) < 32 for c in value) or '\\' in value:
        raise ManifestError(f'Invalid {label}.')
    parts = urlsplit(value)
    if parts.scheme in ('http', 'https') and parts.hostname and not parts.username and not parts.password:
        return value
    if local and value.startswith('/') and not value.startswith('//') and not parts.scheme:
        return value
    raise ManifestError(f'{label} must be HTTP(S)' + (' or a root-relative URL.' if local else '.'))

def artwork(value):
    if value is None:
        return
    if not isinstance(value, dict) or set(value) - {'url', 'path', 'inline', 'alt'}:
        raise ManifestError('Artwork accepts url, path, inline, and alt.')
    sources = [key for key in ('url', 'path', 'inline') if key in value]
    if len(sources) != 1:
        raise ManifestError('Artwork requires exactly one of url, path, or inline.')
    if 'url' in value:
        url(value['url'], 'Artwork URL', local=False)
    if 'path' in value:
        relative_path(value['path'], 'Artwork path')
    if 'inline' in value:
        text(value['inline'], 'Inline artwork')
    if 'alt' in value:
        text(value['alt'], 'Artwork alt text')

def policy(item):
    if item.get('update_policy', 'manual') not in POLICIES:
        raise ManifestError('Unknown update_policy.')
    interval = item.get('refresh_interval', 'never')
    if not isinstance(interval, str) or not re.fullmatch(r'never|[1-9][0-9]*[smhdw]', interval):
        raise ManifestError('refresh_interval must be never or a duration such as 30d.')
    if item.get('update_policy') == 'pin_version':
        text(item.get('version_pin'), 'version_pin')
    if item.get('expected_hash') is not None:
        if not isinstance(item['expected_hash'], str) or not re.fullmatch(r'[0-9a-fA-F]{64}', item['expected_hash']):
            raise ManifestError('expected_hash must be a SHA-256 hex digest when supplied.')
    for name in ('download_url', 'mirror_url', 'online_url', 'source_check_url'):
        if item.get(name):
            url(item[name], name, local=False)

def indexed(values, label):
    if not isinstance(values, list):
        raise ManifestError(f'{label} must be a list.')
    result = {}
    for value in values:
        if not isinstance(value, dict):
            raise ManifestError(f'{label} entries must be mappings.')
        key = value.get('id')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', key) or key in result:
            raise ManifestError(f'{label} IDs must be unique lowercase identifiers.')
        text(value.get('title'), f'{label} title')
        result[key] = value
    return result

def validate_geography(value):
    if not isinstance(value, dict) or set(value) - {'country', 'state', 'counties'}:
        raise ManifestError('geography accepts country, state and counties.')
    if value.get('country') != 'US':
        raise ManifestError('Geographic coverage currently supports country US.')
    state = value.get('state')
    if not isinstance(state, dict) or set(state) != {'code', 'name'}:
        raise ManifestError('geography.state requires code and name.')
    if not isinstance(state['code'], str) or not re.fullmatch(r'[A-Z]{2}', state['code']):
        raise ManifestError('State code must be two uppercase letters.')
    text(state['name'], 'State name')
    counties = value.get('counties')
    if not isinstance(counties, list) or not counties:
        raise ManifestError('geography.counties must be a nonempty list.')
    seen = set()
    for county in counties:
        if not isinstance(county, dict) or set(county) - {'name', 'focus'}:
            raise ManifestError('County entries accept name and optional focus.')
        name = text(county.get('name'), 'County name').strip().casefold()
        if name in seen:
            raise ManifestError('County names must be unique.')
        seen.add(name)
        if 'focus' in county:
            text(county['focus'], 'County focus')


def validate_resource_sections(sections, depth=0):
    if depth > 5 or not isinstance(sections, list):
        raise ManifestError('resource_sections must be lists, nested at most six levels.')
    for section in sections:
        if not isinstance(section, dict) or set(section) - {'title', 'description', 'items', 'sections'}:
            raise ManifestError('Resource sections accept title, description, items and sections.')
        text(section.get('title'), 'Resource section title')
        if 'description' in section:
            text(section['description'], 'Resource section description')
        items = section.get('items', [])
        if not isinstance(items, list):
            raise ManifestError('Resource items must be a list.')
        for item in items:
            if not isinstance(item, dict) or set(item) - {'title', 'path', 'url', 'requires_internet'}:
                raise ManifestError('Resource items accept title, path, url and requires_internet.')
            text(item.get('title'), 'Resource title')
            if ('path' in item) == ('url' in item):
                raise ManifestError('A resource requires exactly one path or URL.')
            if 'path' in item:
                relative_path(item['path'], 'Resource path')
            else:
                url(item['url'])
            if type(item.get('requires_internet', False)) is not bool:
                raise ManifestError('requires_internet must be true or false.')
            if 'path' in item and item.get('requires_internet', False):
                raise ManifestError('SSD resources cannot require internet.')
        if 'sections' in section:
            validate_resource_sections(section['sections'], depth + 1)


def external_link(target, label, css='external-link'):
    """Secondary icon-only destination, with a discoverable accessible name."""
    name = 'Online: ' + label.removesuffix(' (online)')
    glyph = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7M21 3L10 14M10 5H5v14h14v-5"/></svg>'
    return ('<a class="' + css + '" href="' + html.escape(target, quote=True) +
            '" data-requires-internet="true" target="_blank" rel="noopener noreferrer" title="' + html.escape(name, quote=True) +
            '" aria-label="' + html.escape(name, quote=True) + '">' + glyph + '</a>')


def render_resource_sections(sections, root, prefix, hide=False, depth=0):
    rendered = []
    for section in sections:
        heading = min(2 + depth, 6)
        parts = [f'<section class="resource-section"><h{heading}>' +
                 html.escape(section['title']) + f'</h{heading}>']
        if section.get('description'):
            parts.append('<p>' + html.escape(section['description']) + '</p>')
        entries = []
        for item in section.get('items', []):
            title = html.escape(item['title'])
            if 'path' in item:
                local = inside(root, item['path'])
                if not (local.is_file() or local.is_dir()):
                    if not hide:
                        entries.append('<li>' + title + ' <span class="manifest-badge">Unavailable locally</span></li>')
                    continue
                target = prefix + quote(item['path'].rstrip('/'), safe='/') + ('/' if local.is_dir() else '')
                online = False
            else:
                target = item['url']
                online = item.get('requires_internet', not target.startswith('/'))
            attributes = ' data-requires-internet="true"' if online else ''
            if online:
                icon = external_link(target, item['title'])
                if entries:
                    entries[-1] = entries[-1][:-5] + ' ' + icon + '</li>'
                else:
                    entries.append('<li class="reference-external">' + icon + '</li>')
            else:
                entries.append('<li><a href="' + html.escape(target, quote=True) + '"' + attributes + '>' + title + '</a></li>')
        if entries:
            parts.append('<ul>' + ''.join(entries) + '</ul>')
        parts.append(render_resource_sections(section.get('sections', []), root, prefix, hide, depth + 1))
        parts.append('</section>')
        rendered.append(''.join(parts))
    return ''.join(rendered)


def load_manifest(path):
    path = Path(path)
    raw = path.read_text(encoding='utf-8-sig')
    if len(raw.encode('utf-8')) > 16 * 1024 * 1024:
        raise ManifestError('Manifest exceeds 16 MiB.')
    try:
        data = yaml.load(raw, Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise ManifestError(f'Invalid YAML: {error}') from None
    if not isinstance(data, dict):
        raise ManifestError('Manifest must be a mapping.')
    if data.get('format')=='dataark-project-v1':
        from app.services.configuration_project import load
        try:data=load(path)
        except (ValueError,OSError,KeyError,yaml.YAMLError) as error:raise ManifestError('Invalid configuration project: '+str(error)) from None
    community = data.get('community', {'enabled': True})
    if not isinstance(community, dict) or set(community)!={'enabled'} or type(community.get('enabled', True)) is not bool:
        raise ManifestError('community accepts only enabled: true or false.')
    system = data.get('system')
    if not isinstance(system, dict) or system.get('version') != '1.4':
        raise ManifestError('Set system.version to the quoted string "1.4".')
    text(system.get('project_name'), 'system.project_name')
    mount = text(system.get('base_mount'), 'system.base_mount')
    if not PurePosixPath(mount).is_absolute():
        raise ManifestError('system.base_mount must be an absolute path.')
    if type(system.get('hide_missing', False)) is not bool:
        raise ManifestError('system.hide_missing must be true or false.')
    services = system.get('services', {})
    if not isinstance(services, dict):
        raise ManifestError('system.services must be a mapping.')
    port = services.get('kiwix_port', 8080)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ManifestError('kiwix_port must be an integer port.')
    prefix = services.get('content_url_prefix', '/library-files/')
    if not isinstance(prefix, str) or not prefix.startswith('/') or prefix.startswith('//') or '\\' in prefix or '?' in prefix or '#' in prefix:
        raise ManifestError('content_url_prefix must be a root-relative path.')
    artwork(system.get('artwork'))
    categories = indexed(data.get('categories', []), 'categories')
    scenarios = indexed(data.get('scenarios', []), 'scenarios')
    repositories = indexed(data.get('repositories', []), 'repositories')
    assets = indexed(data.get('assets', []), 'assets')
    for repo in repositories.values():
        if repo.get('category') not in categories:
            raise ManifestError(f'Unknown category for repository {repo["id"]}.')
        if type(repo.get('enabled', True)) is not bool:
            raise ManifestError('Repository enabled must be true or false.')
        if type(repo.get('collapse_assets', False)) is not bool:
            raise ManifestError('Repository collapse_assets must be true or false.')
        if not isinstance(repo.get('links', []), list):
            raise ManifestError('Repository links must be a list.')
        for link in repo.get('links', []):
            if not isinstance(link, dict):
                raise ManifestError('Repository links must be mappings.')
            text(link.get('title'), 'Link title')
            if 'service' in link:
                if link['service'] != 'kiwix' or 'url' in link:
                    raise ManifestError('Service links support kiwix plus path, without url.')
                target = link.get('path', '/')
                if not url(target).startswith('/'):
                    raise ManifestError('Service link path must be root-relative.')
            else:
                url(link.get('url'))
            if type(link.get('requires_internet', False)) is not bool:
                raise ManifestError('requires_internet must be true or false.')
        artwork(repo.get('artwork'))
        policy(repo)
    from app.services.collection_variants import groups as variant_groups
    try:
        variant_groups(data)
    except ValueError as error:
        raise ManifestError(str(error)) from error
    for asset in assets.values():
        if asset.get('repository_id') not in repositories:
            raise ManifestError(f'Unknown repository_id for asset {asset["id"]}.')
        if asset.get('category') not in categories:
            raise ManifestError(f'Unknown category for asset {asset["id"]}.')
        relative_path(asset.get('relative_path'), 'Asset relative_path')
        if asset.get('service_endpoint'):
            url(asset['service_endpoint'], 'service_endpoint')
        artwork(asset.get('artwork'))
        # Inherit update policy metadata from the parent; no updates run here.
        parent = repositories[asset['repository_id']]
        for key, default in (('update_policy', 'manual'), ('refresh_interval', 'never'), ('version_pin', None)):
            asset.setdefault(key, parent.get(key, default))
        policy(asset)
    for item in [*repositories.values(), *assets.values()]:
        for field in ('tags', 'scenarios'):
            values = item.get(field, [])
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise ManifestError(f'{field} must be a list of strings.')
        if any(value not in scenarios for value in item.get('scenarios', [])):
            raise ManifestError('Unknown scenario reference.')
    from app.services.bugout import validate as validate_bugout
    try:
        validate_bugout(data.get('bugout', {}))
    except ValueError as error:
        raise ManifestError(str(error)) from None
    if 'geography' in data:
        validate_geography(data['geography'])
    if 'maps' in data:
        from tools.map_worker import settings
        try:
            settings(data)
        except ValueError as error:
            raise ManifestError(str(error)) from None
    from app.services.personalization import validate as validate_personalization
    validate_personalization(data, ManifestError, url)
    from app.services.dashboard_cards import validate as validate_dashboard
    validate_dashboard(data, ManifestError, url)
    validate_resource_sections(data.get('resource_sections', []))
    return data

def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_stat = path.stat() if path.exists() else None
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.manifest-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.chmod(0o644)
        if previous_stat and hasattr(os, 'geteuid') and os.geteuid() == 0:
            os.chown(temporary, previous_stat.st_uid, previous_stat.st_gid)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def image_format(blob):
    if not blob or len(blob) > MAX_IMAGE:
        raise ManifestError('Artwork must be between 1 byte and 5 MiB.')
    try:
        with Image.open(io.BytesIO(blob)) as image:
            if image.format not in FORMATS or image.width * image.height > 25_000_000:
                raise ManifestError('Use PNG, JPEG, GIF, or WebP artwork up to 25 megapixels.')
            result = FORMATS[image.format]
            image.verify()
            return result
    except ManifestError:
        raise
    except Exception:
        raise ManifestError('Artwork is not a valid supported image.') from None

def download_artwork(address):
    request = Request(address, headers={'User-Agent': 'DataArk-Manifest/1.4'})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.geturl()).scheme not in ('http', 'https'):
            raise ManifestError('Artwork redirected to an unsupported scheme.')
        return response.read(MAX_IMAGE + 1)

def prepare_artwork(spec, project_root, output_root, cache, refresh=False):
    if spec is None:
        return None
    if 'path' in spec:
        source = inside(project_root, spec['path'])
        if source.stat().st_size > MAX_IMAGE:
            raise ManifestError('Local artwork exceeds 5 MiB.')
        blob = source.read_bytes()
    elif 'inline' in spec:
        match = re.fullmatch(r'data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=\s]+)', spec['inline'])
        if not match:
            raise ManifestError('Inline artwork must be a base64 PNG/JPEG/GIF/WebP data URI.')
        try:
            blob = base64.b64decode(re.sub(r'\s+', '', match[2]), validate=True)
        except ValueError:
            raise ManifestError('Invalid inline artwork encoding.') from None
        if image_format(blob)[1] != match[1]:
            raise ManifestError('Inline artwork MIME type does not match its bytes.')
    else:
        cached = cache / (hashlib.sha256(spec['url'].encode()).hexdigest() + '.image')
        blob = cached.read_bytes() if cached.is_file() else None
        if blob is not None:
            image_format(blob)
        if blob is None or refresh:
            try:
                fetched = download_artwork(spec['url'])
                image_format(fetched)
                atomic_write(cached, fetched)
                blob = fetched
            except Exception:
                if blob is None:
                    raise ManifestError('Artwork could not be downloaded and has no cached copy: ' + spec['url']) from None
                warnings.warn('Artwork refresh failed; retaining cached copy: ' + spec['url'])
    extension, _ = image_format(blob)
    name = hashlib.sha256(blob).hexdigest() + '.' + extension
    atomic_write(output_root / 'assets' / 'manifest' / name, blob)
    return {'src': 'assets/manifest/' + name, 'alt': spec.get('alt', '')}

def image_tag(art, fallback):
    if not art:
        return ''
    return '<img class="manifest-artwork" src="' + html.escape(art['src'], quote=True) + '" alt="' + html.escape(art['alt'] or fallback, quote=True) + '" loading="lazy">'

def version_dashboard_assets(page, static=None):
    static = Path(static) if static is not None else Path(__file__).resolve().parents[1] / 'static'
    def version(match):
        attribute, relative = match.groups()
        path = static / relative.lstrip('/')
        if not path.is_file():
            return match.group(0)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return f'{attribute}="{relative}?v={digest}"'
    return re.sub(r'(src|href)="(/?assets/(?:js|css)/[A-Za-z0-9_.-]+\.(?:js|css))(?:\?v=[^" ]*)?"', version, page)


def build(manifest_path, template_path, output_path, content_root=None, refresh_artwork=False):
    manifest_path, output_path = Path(manifest_path).resolve(), Path(output_path).resolve()
    data = load_manifest(manifest_path)
    # Split projects live at config/library/ark.yaml; artwork/cache stay repo-relative.
    project_root=manifest_path.parent
    if manifest_path.name=='ark.yaml' and manifest_path.parent.name=='library' and manifest_path.parent.parent.name=='config':project_root=manifest_path.parents[2]
    system = data['system']
    root = Path(content_root or system['base_mount']).resolve()
    cache = project_root / '.cache' / 'artwork'
    destination = output_path.parent
    prefix = system.get('services', {}).get('content_url_prefix', '/library-files/').rstrip('/') + '/'
    port = system.get('services', {}).get('kiwix_port', 8080)
    hide = system.get('hide_missing', False)
    background = prepare_artwork(system.get('artwork'), project_root, destination, cache, refresh_artwork)
    upstream_path = project_root / '.cache/manifest-upstream.json'
    upstream = read_state(upstream_path)
    batch = read_batch(upstream_path)
    asset_rows = {}
    compiled_assets = []
    for asset in data.get('assets', []):
        if asset.get('removed'):
            continue
        local = inside(root, asset['relative_path'])
        available = local.is_file() or local.is_dir()
        art = prepare_artwork(asset.get('artwork'), project_root, destination, cache, refresh_artwork)
        compiled = {**asset, 'available': available, 'artwork': art,
                    'upstream': asset_state(asset, upstream),
                    'local_url': prefix + quote(asset['relative_path'], safe='/') if available else None,
                    'actual_bytes': local.stat().st_size if local.is_file() else None}
        compiled_assets.append(compiled)
        asset_rows.setdefault(asset['repository_id'], []).append(compiled)
    from app.services.dashboard_cards import compose
    display_repositories, display_rows = compose(data, asset_rows)
    sections = []
    source_check_summary = '<span class="source-check-summary">Last checked: <span id="source-check-time">Not yet</span></span>'
    if batch and any(item['upstream']['checked_at'] for item in compiled_assets):
        finished = batch[1].isoformat(timespec='seconds')
        source_check_summary = ('<span class="source-check-summary">Last checked: <span id="source-check-time"><time data-local-time datetime="' +
                        html.escape(finished, quote=True) + '">' +
                        html.escape(batch[1].strftime('%Y-%m-%d %H:%M %Z')) + '</time></span></span>')
    source_check_button = '<button type="button" id="source-check-now" class="source-check-now" title="Check sources now" aria-label="Check sources now"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10a8 8 0 1 0-1.7 7.2"/><path d="M20 4v6h-6"/></svg></button>'
    source_check_status = '<span id="source-check-status" class="source-check-status" role="status" aria-live="polite"></span>'
    for category in data.get('categories', []):
        cards = []
        for repo in display_repositories:
            if not repo.get('enabled', True) or repo['category'] != category['id']:
                continue
            items = display_rows.get(repo['id'], [])
            ready = sum(item['available'] for item in items)
            missing = bool(items) and ready == 0
            if hide and missing:
                continue
            art = prepare_artwork(repo.get('artwork'), project_root, destination, cache, refresh_artwork)
            links = []
            for link in repo.get('links', []):
                online = link.get('requires_internet', False)
                attributes = ' data-requires-internet="true"' if online else ''
                if link.get('service') == 'kiwix':
                    target = f'http://dataark:{port}' + link.get('path', '/')
                    attributes = f' data-manifest-kiwix-port="{port}" data-manifest-kiwix-path="{html.escape(link.get("path", "/"), quote=True)}"'
                else:
                    target = link['url']
                label = html.escape(link['title'])
                if missing and not online:
                    links.append('<span class="manifest-disabled" aria-disabled="true">' + label + '</span>')
                elif online:
                    links.append(external_link(target, link['title']))
                else:
                    links.append('<a href="' + html.escape(target, quote=True) + '"' + attributes + '>' + label + '</a>')
            grouped_links=[]
            for group in repo.get('link_groups',[]):
                group_links=[]
                for link in group['links']:
                    if link.get('service')=='kiwix':
                        path=link.get('path','/');target=f'http://dataark:{port}'+path
                        attrs=f' data-manifest-kiwix-port="{port}" data-manifest-kiwix-path="{html.escape(path,quote=True)}"'
                    else:target=link['url'];attrs=''
                    group_links.append(external_link(target,link['title']) if link.get('requires_internet') else '<a href="'+html.escape(target,quote=True)+'"'+attrs+'>'+html.escape(link['title'])+'</a>')
                grouped_links.append('<div class="manifest-link-group"><h4>'+html.escape(group['title'])+'</h4><nav class="manifest-links" aria-label="'+html.escape(group['title'],quote=True)+'">'+' '.join(group_links)+'</nav></div>')
            entries = []
            for item in items:
                if hide and not item['available']:
                    continue
                title = html.escape(item['title'])
                thumbnail = image_tag(item['artwork'], item['title'])
                observation = item['upstream']
                state = observation['status']
                label = 'Source unavailable' if state == 'unavailable' else 'Source OK' if state == 'available' else 'Source unknown'
                checked = observation['checked_at']
                checked_text = ''
                if checked:
                    fallback = datetime.fromisoformat(checked).strftime('%Y-%m-%d %H:%M UTC')
                    checked_text = '<time data-local-time datetime="' + html.escape(checked, quote=True) + '">' + html.escape(fallback) + '</time>'
                recent = bool(batch and checked and batch[0] <= datetime.fromisoformat(checked) <= batch[1])
                if recent and state == 'available':
                    note = '<span class="manifest-upstream" data-source-asset="' + html.escape(item['id'], quote=True) + '" hidden></span>'
                else:
                    label = label if checked else 'Source unchecked'
                    older = bool(batch and checked and datetime.fromisoformat(checked) < batch[0])
                    detail = ('Older check · ' if older else '') + label
                    if checked and not recent:
                        detail += ' · ' + checked_text
                    note = '<span class="manifest-upstream" data-source-asset="' + html.escape(item['id'], quote=True) + '" title="Online source status at last check. Preserved locally when marked available above.">' + detail + '</span>'
                external = ''
                source = item.get('online_url')
                if source:
                    external = external_link(source, item['title'], 'asset-external')
                if item['available']:
                    attributes = ''
                    if Path(item['relative_path']).suffix.lower() == '.zim':
                        reader_path = '/content/' + quote(Path(item['relative_path']).stem, safe='')
                        target = f'http://dataark:{port}' + reader_path
                        attributes = f' data-manifest-kiwix-port="{port}" data-manifest-kiwix-path="{html.escape(reader_path, quote=True)}"'
                    elif item.get('service_endpoint'):
                        target = data.get('dashboard',{}).get('asset_links',{}).get(item['id'],item['service_endpoint'])
                    elif Path(item['relative_path']).suffix.lower() in ('.pdf', '.html', '.htm', '.txt', '.png', '.jpg', '.jpeg', '.webp'):
                        target = item['local_url']
                    else:
                        target = prefix + 'START-HERE.html'
                    entries.append('<li>' + thumbnail + '<a href="' + html.escape(target, quote=True) + '"' + attributes + '>' + title + '</a>' + external + note + '</li>')
                else:
                    entries.append('<li class="manifest-missing">' + thumbnail + title + external + '<span class="manifest-badge">Unavailable / Pending Download</span>' + note + '</li>')
            badge = 'Unavailable / Pending Download' if missing else f'{ready} of {len(items)} assets available' if items else 'Reference links'
            tags = ''.join('<span class="manifest-tag">' + html.escape(value) + '</span>' for value in repo.get('tags', []))
            asset_list = '<ul class="manifest-assets">' + ''.join(entries) + '</ul>'
            availability = '<span class="manifest-badge">' + badge + '</span>'
            if entries:
                availability = '<details class="manifest-file-details"><summary>' + badge + '</summary>' + asset_list + '</details>'
                asset_list = ''
            cards.append('<article class="manifest-card' + (' manifest-missing' if missing else '') + '" data-repository-id="' + html.escape(repo['id'], quote=True) + '">' +
                         image_tag(art, repo['title']) + '<h3>' + html.escape(repo['title']) + '</h3><p>' +
                         html.escape(str(repo.get('description', ''))) + '</p>' + availability +
                         '<div class="manifest-tags">' + tags + '</div><nav class="manifest-links">' + ' '.join(links) +
                         '</nav>' + ''.join(grouped_links) + asset_list + '</article>')
        if cards:
            heading = '<h2>' + html.escape(category['title']) + '</h2>'
            if category['title'] == 'Content sources':
                heading = '<div class="source-heading">' + heading + source_check_summary + source_check_button + source_check_status + '</div>'
            sections.append('<section class="manifest-category">' + heading + '<p>' +
                            html.escape(str(category.get('description', ''))) + '</p><div class="manifest-grid">' +
                            ''.join(cards) + '</div></section>')
    template = Path(template_path).read_text(encoding='utf-8')
    for token in ('{{PROJECT_NAME}}', '{{MANIFEST_CARDS}}', '{{BACKGROUND_STYLE}}'):
        if token not in template:
            raise ManifestError('Dashboard template is missing ' + token)
    style = '<style>body{background-image:url("' + background['src'] + '")}</style>' if background else ''
    rendered = template.replace('{{PROJECT_NAME}}', html.escape(system['project_name'])).replace('{{MANIFEST_CARDS}}',
        ''.join(sections) or '<p class="manifest-empty">No repositories configured for display.</p>').replace('{{BACKGROUND_STYLE}}', style)
    rendered = rendered.replace('{{RESOURCE_SECTIONS}}', render_resource_sections([section for section in data.get('resource_sections', []) if section['title'] not in data.get('dashboard',{}).get('merged_resource_titles',[])], root, prefix, hide))
    community_enabled = data.get('community', {}).get('enabled', True)
    community_card = '<section id="community-board" class="resource-section" aria-labelledby="community-heading"><h2 id="community-heading">Community</h2><div class="manifest-grid"><article class="manifest-card"><h3>💬 Community board</h3><p>Local announcements, requests, offers, and conversations. Everyone can read and post, even without internet.</p><p><a href="/community.html">Open the community board</a></p></article></div></section>'
    rendered = rendered.replace('{{COMMUNITY_CARD}}', community_card if community_enabled else '').replace('{{COMMUNITY_NAV}}', ' · <a href="/community.html">Community board</a>' if community_enabled else '')
    rendered = version_dashboard_assets(rendered)
    compiled = {**data, 'assets': compiled_assets}
    # Complete validation/rendering before replacing the previously working page.
    atomic_write(destination / 'manifest.json', json.dumps(compiled, indent=2, ensure_ascii=False).encode('utf-8'))
    atomic_write(output_path, rendered.encode('utf-8'))
    return compiled
