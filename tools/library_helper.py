#!/opt/dataark/venv/bin/python
"""Fixed-scope authenticated library install boundary; no caller URLs or paths."""
import fcntl
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,'/opt/dataark')
import yaml
from app.services.library import PACKAGES, ROOT
from app.services.manifest import atomic_write, load_manifest
from tools.update_worker import release_info

def register(payload):
    if not isinstance(payload,dict) or set(payload)!={'repository_id','release','bytes'}:
        raise ValueError('Invalid library request')
    repo=payload['repository_id']
    if repo not in PACKAGES:
        raise ValueError('Unsupported collection')
    spec=PACKAGES[repo]
    with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another update is running. Wait for it to finish and retry.') from None
        data=load_manifest(ROOT/'dataark.yaml')
        if any(a['repository_id']==repo for a in data['assets']):
            return {'message':'This collection is already registered. Its download will resume automatically when the Ark is online.'}
        mount=Path(data['system']['base_mount'])
        if not mount.is_mount():
            raise ValueError('The content SSD must be mounted first.')
        asset={'id':spec['id'],'repository_id':repo,'category':'zim_archives','title':spec['title'],
            'relative_path':spec['prefix']+'2000-01.zim', 'update_policy':'on_network_available','refresh_interval':'1d',
            'update_source':{'kind':'kiwix_zim','directory':spec['directory'],'filename_prefix':spec['prefix']}}
        release=release_info(asset)
        if payload['release']!=release['filename'] or type(payload['bytes']) is not int or payload['bytes']!=release['bytes']:
            raise ValueError('The publisher release changed. Check available downloads again before confirming.')
        import shutil
        if shutil.disk_usage(mount).free < release['bytes']+2*1024**3:
            raise ValueError('Not enough free space, including the verification reserve.')
        asset.update(relative_path=release['filename'],download_url=release['url'],expected_hash=release['sha256'])
        repository=next(r for r in data['repositories'] if r['id']==repo)
        repository['enabled']=True
        repository['description']=spec['description']
        repository['links'].insert(0,{'title':'Read books (local)','service':'kiwix','path':'/#name='+spec['prefix'].rstrip('_')})
        data['assets'].append(asset)
        content=yaml.safe_dump(data,sort_keys=False,allow_unicode=True)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w',suffix='.yaml',dir=ROOT,delete=False) as check:
            check.write(content)
            temporary=Path(check.name)
        try:
            load_manifest(temporary)
        finally:
            temporary.unlink()
        atomic_write(ROOT/'dataark.yaml',content.encode())
    subprocess.run(['/usr/bin/systemctl','start','--no-block','dataark-update.service'],check=True)
    return {'message':'Download requested. It will appear on the landing page after verification and activation. Interrupted downloads resume automatically.'}

if __name__=='__main__':
    try:
        value=sys.stdin.read(2049)
        if len(value)>2048:
            raise ValueError('Request too large')
        print(json.dumps(register(json.loads(value))))
    except Exception as error:
        print(str(error))
        raise SystemExit(1)
