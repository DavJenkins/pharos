"""Local library inventory and a fixed catalogue of supported downloads."""
from pathlib import Path
import json
import shutil
import subprocess
from app.services.manifest import load_manifest
from app.services.update_status import progress

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = {
    'project-gutenberg': {'id':'gutenberg-en', 'title':'Project Gutenberg — English',
        'description':'English-language books in a searchable Kiwix archive. Project Gutenberg terms and individual book notices apply; copyright status varies outside the United States.',
        'directory':'https://download.kiwix.org/zim/gutenberg/', 'prefix':'gutenberg_en_all_',
        'language':'English', 'coverage':'English book collection'},
}

def inventory():
    data = load_manifest(ROOT / 'dataark.yaml')
    mount = Path(data['system']['base_mount'])
    repositories = {r['id']:r for r in data['repositories']}
    installed, pending = [], []
    for asset in data['assets']:
        path = mount / asset['relative_path']
        item = {'title':asset['title'], 'repository':repositories[asset['repository_id']]['title'],
            'id':asset['id'], 'bytes':path.stat().st_size if path.is_file() else None}
        if path.is_file():
            installed.append(item)
        elif asset.get('update_source'):
            pending.append(item)
    usage = shutil.disk_usage(mount)
    return {'installed':installed, 'pending':pending, 'free_bytes':usage.free,
        'storage_ready':mount.is_mount(), 'downloads_enabled':Path('/usr/local/libexec/dataark-library').is_file(), 'progress':progress()}

def catalogue():
    from tools.update_worker import release_info
    data = load_manifest(ROOT / 'dataark.yaml')
    result = []
    for repo, spec in PACKAGES.items():
        item = {k:v for k,v in spec.items() if k not in ('directory','prefix')}
        item['repository_id'] = repo
        item['registered'] = any(a['repository_id'] == repo for a in data['assets'])
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
        input=json.dumps(payload), capture_output=True, text=True, timeout=65)
    if result.returncode:
        raise ValueError(result.stdout.strip() or 'Library installation request failed.')
    return json.loads(result.stdout)
