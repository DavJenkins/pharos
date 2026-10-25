"""Local library inventory and a fixed catalogue of supported downloads."""
from pathlib import Path
import json
import shutil
import subprocess
import math
import time
from datetime import datetime, timezone
from app.services.manifest import load_manifest
from app.services.update_status import progress

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = {
    'project-gutenberg': {'id':'gutenberg-en', 'title':'Project Gutenberg — English',
        'description':'English-language books in a searchable Kiwix archive. Project Gutenberg terms and individual book notices apply; copyright status varies outside the United States.',
        'directory':'https://download.kiwix.org/zim/gutenberg/', 'prefix':'gutenberg_en_all_',
        'language':'English', 'coverage':'English book collection'},
}

CHECK_HISTORY = Path('/var/lib/dataark/updates/checked.json')

def update_schedule(asset, repository, history, history_available=True, now=None):
    from tools.update_worker import interval_seconds
    policy=asset.get('update_policy',repository.get('update_policy','manual'))
    interval=asset.get('refresh_interval',repository.get('refresh_interval','never'))
    seconds=interval_seconds(interval)
    enabled=policy!='manual' and seconds is not None and repository.get('enabled',True) and not asset.get('removed',False)
    checked=history.get(asset['id'])
    last=None
    if checked is not None:
        try:
            if type(checked) not in (int,float) or not math.isfinite(checked) or checked<=0:
                raise ValueError('Invalid check timestamp')
            last=datetime.fromtimestamp(checked,timezone.utc).isoformat(timespec='seconds')
        except (ValueError,OverflowError,OSError):
            checked=None
            history_available=False
    due=None
    if enabled and checked is not None and history_available:
        try:
            due=datetime.fromtimestamp(checked+seconds,timezone.utc).isoformat(timespec='seconds')
        except (ValueError,OverflowError,OSError):
            history_available=False
    return {'policy':policy,'interval':interval,'enabled':bool(enabled),'last_checked':last,
        'next_due':due,'due_now':bool(enabled and history_available and (checked is None or checked+seconds <= (time.time() if now is None else now))),
        'history_available':history_available,'pinned_version':asset.get('version_pin')}


def inventory():
    data = load_manifest(ROOT / 'dataark.yaml')
    mount = Path(data['system']['base_mount'])
    repositories = {r['id']:r for r in data['repositories']}
    try:
        history=json.loads(CHECK_HISTORY.read_text())
        if not isinstance(history,dict):
            raise ValueError('Invalid history')
        history_available=True
    except FileNotFoundError:
        history,history_available={},True
    except (OSError,ValueError):
        history,history_available={},False
    installed, pending, removed = [], [], []
    from app.services import reference_checks
    reference_config = reference_checks.settings()
    reference_state = reference_checks.read(reference_checks.STATE, {'sources': {}})
    for asset in data['assets']:
        path = mount / asset['relative_path']
        item = {'title':asset['title'], 'repository':repositories[asset['repository_id']]['title'],
            'id':asset['id'], 'repository_id':asset['repository_id'], 'relative_path':asset['relative_path'], 'can_restore':bool(asset.get('update_source')), 'source_url':asset.get('download_url'), 'bytes':path.stat().st_size if path.is_file() else None}
        item['update']=update_schedule(asset,repositories[asset['repository_id']],history,history_available)
        reference = reference_checks.projection(asset, repositories[asset['repository_id']], reference_config, reference_state, time.time())
        if reference is not None:
            item['update'] = reference
        if asset.get('removed'):
            removed.append(item)
        elif path.is_file():
            installed.append(item)
        elif asset.get('update_source'):
            pending.append(item)
    usage = shutil.disk_usage(mount)
    return {'installed':installed, 'pending':pending, 'removed':removed, 'free_bytes':usage.free, 'total_bytes':usage.total, 'used_bytes':usage.used,
        'storage_ready':mount.is_mount(), 'downloads_enabled':Path('/usr/local/libexec/dataark-library').is_file(), 'progress':progress()}

def catalogue():
    from tools.update_worker import release_info
    data = load_manifest(ROOT / 'dataark.yaml')
    result = []
    for repo, spec in PACKAGES.items():
        # Existing and removed collections are managed in their own inventory lists.
        if any(a['repository_id']==repo for a in data['assets']):
            continue
        item = {k:v for k,v in spec.items() if k not in ('directory','prefix')}
        item['repository_id'] = repo
        item['registered'] = any(a['repository_id'] == repo and not a.get('removed') for a in data['assets'])
        try:
            release = release_info({'id':spec['id'], 'relative_path':spec['prefix']+'2000-01.zim',
                'update_source':{'kind':'kiwix_zim','directory':spec['directory'],'filename_prefix':spec['prefix']}})
            item.update(release=release['filename'], bytes=release['bytes'])
        except Exception:
            item['error'] = 'Cannot check the publisher right now. Connect the Ark to the internet and retry.'
        result.append(item)
    return result

def install(payload):
    result = subprocess.run(['/usr/bin/sudo','-n','--','/usr/local/libexec/dataark-library'],
        input=json.dumps(payload), capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError(result.stdout.strip() or 'Library installation request failed.')
    return json.loads(result.stdout)
