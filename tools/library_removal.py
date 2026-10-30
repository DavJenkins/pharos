"""Transactional removal of one registered file, with recovery before updates."""
import json
from pathlib import Path
import subprocess
import tempfile
import yaml
from app.services.library_events import tracked, phase, emit
from app.services.manifest import atomic_write, load_manifest, inside
from tools.activate_content_updates import check_container, docker, wait_for_library
from tools.publish_content import publish

ROOT=Path(__file__).resolve().parents[1]
MOUNT=Path('/mnt/storage')
JOURNAL=Path('/var/lib/dataark/updates/removal.json')

class ManifestDumper(yaml.SafeDumper):
    def increase_indent(self,flow=False,indentless=False):
        return super().increase_indent(flow,False)

def serialize(data):
    text=yaml.dump(data,Dumper=ManifestDumper,sort_keys=False,allow_unicode=True)
    with tempfile.NamedTemporaryFile(mode='w',suffix='.yaml',dir=ROOT,delete=False) as stream:
        stream.write(text)
        candidate=Path(stream.name)
    try:
        load_manifest(candidate)
    finally:
        candidate.unlink()
    return text

def target(data,asset_id,relative,expected_bytes):
    asset=next((a for a in data['assets'] if a['id']==asset_id),None)
    if asset is None or asset.get('removed') or asset['relative_path']!=relative:
        raise ValueError('Collection changed. Reload the library before removing it.')
    mount=Path(data['system']['base_mount'])
    if mount!=MOUNT or mount.is_symlink() or not mount.is_mount():
        raise ValueError('The content SSD must be mounted.')
    raw=mount/relative
    path=inside(mount,relative)
    if raw.is_symlink() or raw.absolute()!=path or not path.is_file():
        raise ValueError('Only registered regular files on the content SSD can be removed.')
    if type(expected_bytes) is not int or path.stat().st_size!=expected_bytes:
        raise ValueError('File size changed. Reload the library before confirming removal.')
    if any(a['id']!=asset_id and a['relative_path']==relative and not a.get('removed') for a in data['assets']):
        raise ValueError('This file is shared by another collection and cannot be removed separately.')
    return asset,path

def publish_library(mount):
    publish(mount)
    subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)

def recover():
    if not JOURNAL.exists():
        return
    state=json.loads(JOURNAL.read_text())
    emit('recovery_started',phase=state['phase'])
    mount=MOUNT
    path=inside(mount,state['relative_path'])
    saved=mount/'.dataark-updates'/'removed-file'
    if saved.is_symlink() or path.is_symlink():
        raise ValueError('Unsafe removal recovery path')
    if state['phase']=='committed':
        saved.unlink(missing_ok=True)
        JOURNAL.unlink()
        emit('recovery_completed',outcome='committed removal cleanup')
        return
    if saved.exists():
        if path.exists():
            raise ValueError('Removal recovery destination already exists')
        saved.rename(path)
    atomic_write(ROOT/'dataark.yaml',state['original'].encode())
    if state['zim']:
        docker('restart','kiwix-serve')
        wait_for_library([{'filename':path.name}],[],state['port'])
    publish_library(mount)
    JOURNAL.unlink()
    emit('rollback_completed',outcome='previous content restored')

@tracked('remove')
def remove(payload):
    if set(payload)!={'action','asset_id','relative_path','bytes'} or payload['action']!='remove':
        raise ValueError('Invalid removal request')
    import fcntl
    with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('An update is running. Wait for it to finish before removing content.') from None
        recover()
        manifest=ROOT/'dataark.yaml'
        original=manifest.read_text()
        data=load_manifest(manifest)
        phase('validating registered file')
        asset,path=target(data,payload['asset_id'],payload['relative_path'],payload['bytes'])
        mount=MOUNT
        staging=mount/'.dataark-updates'
        if staging.is_symlink() or (staging/'activation.json').exists():
            raise ValueError('Finish the pending content operation first.')
        staging.mkdir(exist_ok=True)
        with (staging/'.lock').open('a') as stage_lock:
            fcntl.flock(stage_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            saved=staging/'removed-file'
            if saved.exists() or saved.is_symlink():
                raise ValueError('A previous removal needs recovery.')
            zim=path.suffix.lower()=='.zim'
            if zim and not check_container(mount):
                raise ValueError('The local reader must be running before an archive can be removed.')
            asset['removed']=True
            asset['update_policy']='manual'
            asset['refresh_interval']='never'
            repo=next(r for r in data['repositories'] if r['id']==asset['repository_id'])
            if not any(a['repository_id']==repo['id'] and not a.get('removed') for a in data['assets']):
                repo['enabled']=False
            updated=serialize(data)
            state={'phase':'prepared','relative_path':payload['relative_path'],'original':original,'zim':zim,
                'port':data['system']['services']['kiwix_port']}
            atomic_write(JOURNAL,json.dumps(state).encode())
            try:
                phase('staging removal')
                path.rename(saved)
                if zim:
                    phase('restarting local reader')
                    docker('restart','kiwix-serve')
                    phase('confirming reader catalogue')
                    wait_for_library([], [path.name],state['port'])
                phase('disabling automatic updates')
                atomic_write(manifest,updated.encode())
                phase('publishing library and landing page')
                publish_library(mount)
                state['phase']='committed'
                atomic_write(JOURNAL,json.dumps(state).encode())
            except Exception:
                emit('rollback_started')
                recover()
                raise
            phase('freeing storage')
            saved.unlink()
            JOURNAL.unlink()
    return {'message':'Removed from the Ark. Automatic updates for this item are off. Its source information is retained for reinstatement.'}

@tracked('reinstate')
def restore(payload):
    if set(payload)!={'action','asset_id'} or payload['action']!='restore':
        raise ValueError('Invalid reinstatement request')
    import fcntl
    from tools.update_worker import release_info
    with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('An update is running. Wait for it to finish and retry.') from None
        recover()
        data=load_manifest(ROOT/'dataark.yaml')
        asset=next((a for a in data['assets'] if a['id']==payload['asset_id']),None)
        if not asset or not asset.get('removed') or not asset.get('update_source'):
            raise ValueError('This item has no supported automatic download source.')
        mount=Path(data['system']['base_mount'])
        if not mount.is_mount():
            raise ValueError('Content SSD is not mounted')
        asset['update_policy']='on_network_available'
        phase('checking reinstatement source')
        release=release_info(asset)
        import shutil
        if not release or shutil.disk_usage(mount).free<release['bytes']+2*1024**3:
            raise ValueError('A release or sufficient free space is unavailable.')
        asset.pop('removed')
        asset['refresh_interval']='1d'
        repo=next(r for r in data['repositories'] if r['id']==asset['repository_id'])
        repo['enabled']=True
        for option in repo.get('variants',[]):
            if option['asset_id']==asset['id']:repo['preferred_variant']=option['id']
        atomic_write(ROOT/'dataark.yaml',serialize(data).encode())
        history_path=Path('/var/lib/dataark/updates/checked.json')
        history=json.loads(history_path.read_text()) if history_path.exists() else {}
        history.pop(asset['id'],None)
        atomic_write(history_path,json.dumps(history).encode())
    subprocess.run(['/usr/bin/systemctl','start','--no-block','dataark-update.service'],check=True)
    return {'message':'Reinstatement requested. The archive will be downloaded, verified and returned to the landing page.'}


@tracked('variant_preference')
def prefer_variant(payload):
    if set(payload)!={'action','repository_id','variant_id'} or payload['action']!='prefer':raise ValueError('Invalid variant preference request')
    import fcntl
    from app.services.collection_variants import groups
    with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('An update is running. Wait for it to finish.') from None
        data=load_manifest(ROOT/'dataark.yaml');options=groups(data)
        group=next((g for g in options if g['id']==payload['repository_id']),None)
        variant=next((v for v in group['variants'] if v['id']==payload['variant_id']),None) if group else None
        if not variant:raise ValueError('Unknown collection variant')
        asset=next(a for a in data['assets'] if a['id']==variant['asset_id'])
        mount=Path(data['system']['base_mount'])
        if not mount.is_mount() or asset.get('removed') or not inside(mount,asset['relative_path']).is_file():raise ValueError('Download and activate this variant before preferring it for restoration.')
        repo=next(r for r in data['repositories'] if r['id']==group['id']);repo['preferred_variant']=variant['id']
        atomic_write(ROOT/'dataark.yaml',serialize(data).encode())
    subprocess.run([str(ROOT/'venv/bin/python'),'-m','tools.content_profile','export'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    return {'message':'Restoration preference saved. Existing copies were kept.'}
