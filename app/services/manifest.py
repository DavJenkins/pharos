"""Data Ark v1.4 manifest loading and static dashboard rendering.

No content downloads, scheduled updates, or executable launches occur here.
Only explicitly configured artwork can be fetched during a build.
"""
import base64
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
from app.services.upstream import read_state, asset_state

MAX_IMAGE = 5 * 1024 * 1024
POLICIES = {'manual', 'auto', 'pin_version', 'on_network_available'}
FORMATS = {'PNG': ('png', 'image/png'), 'JPEG': ('jpg', 'image/jpeg'),
           'GIF': ('gif', 'image/gif'), 'WEBP': ('webp', 'image/webp')}

class ManifestError(ValueError):
    pass

class UniqueLoader(yaml.SafeLoader):
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
    for name in ('download_url', 'mirror_url'):
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

def build(manifest_path, template_path, output_path, content_root=None, refresh_artwork=False):
    manifest_path, output_path = Path(manifest_path).resolve(), Path(output_path).resolve()
    data = load_manifest(manifest_path)
    system = data['system']
    root = Path(content_root or system['base_mount']).resolve()
    cache = manifest_path.parent / '.cache' / 'artwork'
    destination = output_path.parent
    prefix = system.get('services', {}).get('content_url_prefix', '/library-files/').rstrip('/') + '/'
    port = system.get('services', {}).get('kiwix_port', 8080)
    hide = system.get('hide_missing', False)
    background = prepare_artwork(system.get('artwork'), manifest_path.parent, destination, cache, refresh_artwork)
    upstream = read_state(manifest_path.parent / '.cache/manifest-upstream.json')
    asset_rows = {}
    compiled_assets = []
    for asset in data.get('assets', []):
        local = inside(root, asset['relative_path'])
        available = local.is_file() or local.is_dir()
        art = prepare_artwork(asset.get('artwork'), manifest_path.parent, destination, cache, refresh_artwork)
        compiled = {**asset, 'available': available, 'artwork': art,
                    'upstream': asset_state(asset, upstream),
                    'local_url': prefix + quote(asset['relative_path'], safe='/') if available else None,
                    'actual_bytes': local.stat().st_size if local.is_file() else None}
        compiled_assets.append(compiled)
        asset_rows.setdefault(asset['repository_id'], []).append(compiled)
    sections = []
    for category in data.get('categories', []):
        cards = []
        for repo in data.get('repositories', []):
            if not repo.get('enabled', True) or repo['category'] != category['id']:
                continue
            items = asset_rows.get(repo['id'], [])
            ready = sum(item['available'] for item in items)
            missing = bool(items) and ready == 0
            if hide and missing:
                continue
            art = prepare_artwork(repo.get('artwork'), manifest_path.parent, destination, cache, refresh_artwork)
            links = []
            for link in repo.get('links', []):
                online = link.get('requires_internet', False)
                attributes = ' data-requires-internet="true"' if online else ''
                if link.get('service') == 'kiwix':
                    target = f'http://dataark:{port}' + link.get('path', '/')
                    attributes = f' data-manifest-kiwix-port="{port}" data-manifest-kiwix-path="{html.escape(link.get("path", "/"), quote=True)}"'
                else:
                    target = link['url']
                label = html.escape(link['title']) + (' (online)' if online else '')
                if missing and not online:
                    links.append('<span class="manifest-disabled" aria-disabled="true">' + label + '</span>')
                else:
                    links.append('<a href="' + html.escape(target, quote=True) + '"' + attributes + '>' + label + '</a>')
            entries = []
            for item in items:
                if hide and not item['available']:
                    continue
                title = html.escape(item['title'])
                thumbnail = image_tag(item['artwork'], item['title'])
                observation = item['upstream']
                state = observation['status']
                label = ('Preserved locally — source unavailable' if item['available'] else 'Source unavailable') if state == 'unavailable' else 'Upstream available at last check' if state == 'available' else 'Upstream status unknown'
                checked = observation['checked_at']
                note = '<span class="manifest-upstream">' + label + (' · checked ' + html.escape(checked) if checked else ' · not checked') + '</span>'
                external = ''
                source = item.get('download_url') or item.get('mirror_url')
                if source:
                    glyph = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7M21 3L10 14M10 5H5v14h14v-5"/></svg>'
                    if state == 'unavailable':
                        external = '<span class="asset-external" role="link" aria-disabled="true" tabindex="0" title="Online source unavailable at last check" aria-label="Online source unavailable">' + glyph + '</span>'
                    else:
                        if state == 'available':
                            for result in upstream.get(item['id'], {}).get('observations', []):
                                if result.get('status') == 'available' and result.get('url') in (item.get('download_url'), item.get('mirror_url')):
                                    source = result['url']
                                    break
                        external = '<a class="asset-external" data-requires-internet="true" href="' + html.escape(source, quote=True) + '" target="_blank" rel="noopener noreferrer" title="Open online download source" aria-label="' + html.escape('Open online download source for ' + item['title'], quote=True) + '">' + glyph + '</a>'
                if item['available']:
                    target = item['local_url']
                    reader = (' <a href="' + html.escape(item['service_endpoint'], quote=True) + '">Read</a>') if item.get('service_endpoint') else ''
                    entries.append('<li>' + thumbnail + '<a href="' + html.escape(target, quote=True) + '">' + title + '</a>' + external + reader + note + '</li>')
                else:
                    entries.append('<li class="manifest-missing">' + thumbnail + title + external + '<span class="manifest-badge">Unavailable / Pending Download</span>' + note + '</li>')
            badge = 'Unavailable / Pending Download' if missing else f'{ready} of {len(items)} assets available' if items else 'Reference links'
            tags = ''.join('<span class="manifest-tag">' + html.escape(value) + '</span>' for value in repo.get('tags', []))
            cards.append('<article class="manifest-card' + (' manifest-missing' if missing else '') + '" data-repository-id="' + html.escape(repo['id'], quote=True) + '">' +
                         image_tag(art, repo['title']) + '<h3>' + html.escape(repo['title']) + '</h3><p>' +
                         html.escape(str(repo.get('description', ''))) + '</p><span class="manifest-badge">' + badge +
                         '</span><div class="manifest-tags">' + tags + '</div><nav class="manifest-links">' + ' '.join(links) +
                         '</nav><ul class="manifest-assets">' + ''.join(entries) + '</ul></article>')
        if cards:
            sections.append('<section class="manifest-category"><h2>' + html.escape(category['title']) + '</h2><p>' +
                            html.escape(str(category.get('description', ''))) + '</p><div class="manifest-grid">' +
                            ''.join(cards) + '</div></section>')
    template = Path(template_path).read_text(encoding='utf-8')
    for token in ('{{PROJECT_NAME}}', '{{MANIFEST_CARDS}}', '{{BACKGROUND_STYLE}}'):
        if token not in template:
            raise ManifestError('Dashboard template is missing ' + token)
    style = '<style>body{background-image:url("' + background['src'] + '")}</style>' if background else ''
    rendered = template.replace('{{PROJECT_NAME}}', html.escape(system['project_name'])).replace('{{MANIFEST_CARDS}}',
        ''.join(sections) or '<p class="manifest-empty">No repositories configured for display.</p>').replace('{{BACKGROUND_STYLE}}', style)
    compiled = {**data, 'assets': compiled_assets}
    # Complete validation/rendering before replacing the previously working page.
    atomic_write(destination / 'manifest.json', json.dumps(compiled, indent=2, ensure_ascii=False).encode('utf-8'))
    atomic_write(output_path, rendered.encode('utf-8'))
    return compiled
