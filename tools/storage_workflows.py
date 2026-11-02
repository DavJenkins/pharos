"""Reviewed adoption, migration and replacement of library storage.

Never executes code from a drive and never formats or deletes its content.
Configuration replacement is explicit and keeps a private rollback snapshot.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path('/opt/dataark')
STATE=Path('/var/lib/dataark/storage')
PRIVATE=Path('/etc/dataark/storage')
MARKER='.dataark-storage.json'
SYSTEM_METADATA={'lost+found','System Volume Information','$RECYCLE.BIN'}

def engine():
    from tools.appliance_jobs import storage_module
    return storage_module()

def save(path,value,public=False):
    from tools.clone_drive import save as atomic
    atomic(path,value);path.chmod(0o644 if public else 0o600)

def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def inventory(root,x):return [f for f in x.files(root) if f['path']!=MARKER]

def public_profile(target):
    """Parse portable public data with current installed validators, not drive code."""
    from app.services import configuration_project as project
    from tools import content_profile as content
    from tools.build_bootstrap_release import inspect_config
    folder=target/'DATA-ARK-CONFIG/config/content'
    profile=folder/'content.yaml'
    if not profile.is_file():raise ValueError('Drive lacks its readable Ark content profile')
    c=project.parse(profile.read_text(encoding='utf-8'));content.validate(c)
    manifest=content.inside(folder,c['manifest'])
    public=content.read(manifest);inspect_config(public)
    if not isinstance(public,dict) or any(k not in project.PUBLIC_KEYS for k in public):raise ValueError('Drive manifest contains private or unsupported sections')
    if public.get('system',{}).get('base_mount')!='/mnt/storage':raise ValueError('Drive uses an unsupported library mount layout')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'review.yaml';path.write_text(project.dump(public),encoding='utf-8')
        from app.services.manifest import load_manifest
        public=load_manifest(path)
    # Record every public profile file, refusing links and executable additions.
    snapshots={};total=0
    for path in folder.rglob('*'):
        if path.is_symlink():raise ValueError('Profile contains a symlink')
        if not path.is_file():continue
        if path.suffix not in ('.yaml','.yml','.json','.txt'):raise ValueError('Profile contains executable or unsupported data: '+path.name)
        blob=path.read_bytes();total+=len(blob)
        if total>32*1024**2:raise ValueError('Public profile exceeds 32 MiB')
        snapshots[path.relative_to(folder).as_posix()]=hashlib.sha256(blob).hexdigest()
    return c,public,snapshots

def receipts(target):
    path=target/'CLONE-REPORT.json'
    if path.exists():
        if path.stat().st_size>32*1024**2:raise ValueError('Copy receipt is too large')
        data=json.loads(path.read_text());rows=data.get('files',[])
    else:
        path=target/'DATA-ARK-CONFIG/config/content/content-lock.json'
        if not path.is_file():return {}
        if path.stat().st_size>32*1024**2:raise ValueError('Content lock is too large')
        rows=json.loads(path.read_text()).get('assets',[])
    result={}
    from tools.content_profile import inside
    for item in rows:
        relative=item.get('path');checksum=item.get('sha256')
        if not isinstance(relative,str):raise ValueError('Invalid receipt path')
        inside(target,relative)
        if checksum:
            if not isinstance(checksum,str) or len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):raise ValueError('Invalid content checksum')
            if relative in result and result[relative]!=checksum:raise ValueError('Conflicting checksums for '+relative)
            result[relative]=checksum
    return result

def inspect_source(x):
    mounted=x.SOURCE.is_mount()
    if not mounted and x.SOURCE.exists() and any(x.SOURCE.iterdir()):raise ValueError('Unmounted library directory contains files; inspect them before hiding anything')
    return {'mounted':mounted,'uuid':x.run(['findmnt','-n','-o','UUID','--mountpoint',str(x.SOURCE)]) if mounted else None,
            'device':x.SOURCE.stat().st_dev if mounted else None}

def plan(uuid,mode,configuration='keep',copy_existing=False):
    if mode not in ('adopt','replace') or configuration not in ('keep','drive') or type(copy_existing) is not bool:raise ValueError('Invalid storage choice')
    if mode=='replace' and configuration!='keep':raise ValueError('Replacement storage keeps the saved desired library')
    if mode=='adopt' and copy_existing:raise ValueError('Adoption never overwrites existing drive content')
    x=engine();matches=[d for d in x.devices() if d['uuid']==uuid]
    if len(matches)!=1:raise ValueError('Drive UUID is missing or ambiguous')
    row,target=x.mounted(uuid);source=inspect_source(x);target_files=inventory(target,x)
    source_files=[];checksums={};profile_hashes={};conflicts={}
    if mode=='adopt':
        c,public,profile_hashes=public_profile(target)
        from tools.content_profile import read
        host=read(ROOT/'dataark.yaml');host_ids={a['id']:a for a in host.get('assets',[])};drive_ids={a['id']:a for a in public.get('assets',[])}
        conflicts={'host_assets':len(host_ids),'drive_assets':len(drive_ids),'new_assets':len(drive_ids.keys()-host_ids.keys()),
                   'removed_from_configuration':len(host_ids.keys()-drive_ids.keys()),'changed_assets':sum(host_ids[k]!=drive_ids[k] for k in host_ids.keys()&drive_ids.keys())}
        checksums=receipts(target)
    else:
        marker=target/MARKER
        if marker.exists():
            saved=json.loads(marker.read_text())
            if saved.get('uuid')!=uuid or saved.get('generator')!='dataark-storage-v1':raise ValueError('Unrelated destination preparation marker')
        elif any(p.name not in SYSTEM_METADATA for p in target.iterdir()):raise ValueError('Replacement drive must be empty; use adoption for a populated Ark drive')
        if copy_existing:
            if not source['mounted']:raise ValueError('Reconnect the existing library before choosing to copy it')
            source_files=inventory(x.SOURCE,x)
            required=sum(((f['bytes']+4095)//4096)*4096 for f in source_files)+1024**3
            if required>shutil.disk_usage(target).free+sum(f['bytes'] for f in target_files):raise ValueError('Entire current library plus 1 GiB must fit')
    value={'uuid':uuid,'device':row['device'],'serial':row['serial'],'filesystem':row['filesystem'],'target':str(target),'mode':mode,
           'configuration':configuration,'copy_existing':copy_existing,'source':source,'source_files':source_files,'target_files':target_files,
           'checksums':checksums,'profile_hashes':profile_hashes,'configuration_changes':conflicts,
           'current_manifest_sha256':hashlib.sha256((ROOT/'dataark.yaml').read_bytes()).hexdigest()}
    value['plan_id']=identity(value)
    PRIVATE.mkdir(parents=True,exist_ok=True);PRIVATE.chmod(0o700);save(PRIVATE/'plan.json',value)
    missing=sorted(set(checksums)-{f['path'] for f in target_files})
    return {k:v for k,v in value.items() if k not in ('source_files','target_files','checksums','profile_hashes')}|{
        'target_files_count':len(target_files),'copy_bytes':sum(f['bytes'] for f in source_files),'recorded_checksums':len(checksums),
        'missing_recorded_files':len(missing),'first_missing_files':missing[:20],
        'message':'Nothing formatted or downloaded. Drive hashes verify recorded receipts where available; other files are fingerprinted locally, not authenticated against a publisher.'}

def status(phase,**fields):save(STATE/'status.json',dict(phase=phase,updated=time.time(),**fields),True)

def reconnect():
    x=engine()
    if x.SOURCE.is_mount():return {'message':'The configured library is already mounted.'}
    inspect_source(x)
    rows=[line.split() for line in x.FSTAB.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len([r for r in rows if len(r)>1 and r[1]==str(x.SOURCE)])!=1:raise ValueError('Configured library mount is ambiguous; review storage settings')
    x.run(['mount',str(x.SOURCE)])
    if not x.SOURCE.is_mount():raise ValueError('Configured drive is still unavailable; the saved configuration was retained')
    subprocess.run(['docker','restart','kiwix-serve'],capture_output=True)
    x.run([str(ROOT/'venv/bin/python'),str(ROOT/'tools/render_dashboard.py'),str(ROOT/'dataark.yaml'),'/var/www/html/index.html'])
    status('ready',message='Original configured library reconnected.');return {'message':'Original library reconnected.'}

def mount_entry(text,x,p):
    if any(len(f)>1 and f[1]==str(x.SOURCE) for f in (line.split() for line in text.splitlines()) if f and not f[0].startswith('#')):
        return x.fstab_external(text,p['uuid'],p['filesystem'])
    if p['source']['mounted']:raise ValueError('Mounted library has no persistent entry; inspect before replacement')
    return x.fstab_external(text.rstrip()+'\n# New library placeholder\nnone '+str(x.SOURCE)+' auto noauto 0 0\n',p['uuid'],p['filesystem'])

def restore_backup(journal,x):
    backup=Path(journal['backup'])
    x.FSTAB.write_bytes((backup/'fstab').read_bytes())
    for name in ('dataark.yaml','config/installed-site.json'):
        old=backup/name
        if old.exists():
            dest=ROOT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old.read_bytes())
        elif name=='config/installed-site.json':(ROOT/name).unlink(missing_ok=True)
    for name in ('library','content'):
        old=backup/('config-'+name);live=ROOT/'config'/name
        if old.exists():
            if live.exists():live.rename(backup/('failed-'+name+'-'+str(time.time_ns())) )
            shutil.copytree(old,live)
        elif 'config_trees' in journal and name not in journal['config_trees'] and live.exists():
            live.rename(backup/('failed-'+name+'-'+str(time.time_ns())))

def recover():
    x=engine();path=PRIVATE/'journal.json'
    if not path.exists():return
    journal=json.loads(path.read_text())
    if journal['phase']!='activating':return
    restore_backup(journal,x);x.run(['systemctl','daemon-reload'])
    for args in (['umount',str(x.SOURCE)],['mount',str(x.SOURCE)]):
        try:x.run(args)
        except (ValueError,OSError,subprocess.CalledProcessError):pass
    save(path,{**journal,'phase':'rolled_back'});status('rolled_back',message='Interrupted storage activation restored the previous selection. Both drives retain their content.')

def adopt_configuration(target,p,backup,x):
    if p['configuration']!='drive':return
    c,public,hashes=public_profile(target)
    if hashes!=p['profile_hashes']:raise ValueError('Drive configuration changed after review')
    from tools import content_profile as content
    from app.services import configuration_project as project
    host=content.read(ROOT/'dataark.yaml')
    for key in project.PUBLIC_KEYS:
        if key=='system':continue
        if key in public:host[key]=public[key]
        else:host.pop(key,None)
    # Retain old public authoring trees, including manual edits, in private backup.
    for name in ('library','content'):
        live=ROOT/'config'/name
        if live.exists():live.rename(backup/('displaced-'+name))
    project.write(ROOT/'config/library',host)
    from app.services.manifest import atomic_write
    atomic_write(ROOT/'dataark.yaml',project.dump(host).encode())
    shutil.copytree(target/'DATA-ARK-CONFIG/config/content',ROOT/'config/content')
    c['content_root']='/mnt/storage';content.write(ROOT/'config/content/content.yaml',project.dump(c))

def worker():
    import fcntl
    x=engine();p=json.loads((PRIVATE/'job.json').read_text())
    with contextlib.ExitStack() as stack:
        for lock_path in [x.PRIVATE/'worker.lock']+x.LOCKS:
            lock_path.parent.mkdir(parents=True,exist_ok=True);lock=stack.enter_context(lock_path.open('a'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if inspect_source(x)!=p['source'] or hashlib.sha256((ROOT/'dataark.yaml').read_bytes()).hexdigest()!=p['current_manifest_sha256']:raise ValueError('Current library changed; review again')
        row,target=x.mounted(p['uuid']);dev=target.stat().st_dev
        if row['device']!=p['device'] or row['serial']!=p['serial'] or inventory(target,x)!=p['target_files']:raise ValueError('Destination changed after review')
        def guard():
            if not target.is_mount() or target.stat().st_dev!=dev:raise ValueError('Destination disconnected')
        backup=PRIVATE/('rollback-'+str(time.time_ns()));backup.mkdir(mode=0o700)
        shutil.copy2(x.FSTAB,backup/'fstab')
        for name in ('dataark.yaml','config/installed-site.json'):
            path=ROOT/name
            if path.exists():dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        for name in ('library','content'):
            folder=ROOT/'config'/name
            if folder.exists():shutil.copytree(folder,backup/('config-'+name))
        journal={'phase':'preparing','backup':str(backup),'uuid':p['uuid'],'config_trees':[n for n in ('library','content') if (backup/('config-'+n)).exists()]};save(PRIVATE/'journal.json',journal)
        active,reader=x.quiesce()
        try:
            status('verifying',message='Checking the selected storage and recorded hashes.')
            if p['mode']=='adopt':
                for i,item in enumerate(p['target_files']):
                    guard();path=target/item['path'];checksum=x.digest(path)
                    if item['path'] in p['checksums'] and checksum!=p['checksums'][item['path']]:raise ValueError('Recorded checksum mismatch: '+item['path'])
                    if i%20==0:status('verifying',completed_files=i,total_files=len(p['target_files']))
            elif p['copy_existing']:
                if inventory(x.SOURCE,x)!=p['source_files']:raise ValueError('Original library changed after review')
                save(target/MARKER,{'generator':'dataark-storage-v1','uuid':p['uuid']},True)
                x.copy_verified(x.SOURCE,target,p['source_files'],guard,lambda n,total:status('copying',completed_files=n,total_files=total,percent=round(n*100/max(total,1))))
            guard();journal['phase']='activating';save(PRIVATE/'journal.json',journal)
            if p['mode']=='adopt':adopt_configuration(target,p,backup,x)
            new=mount_entry(x.FSTAB.read_text(),x,p)
            x.run(['umount',str(target)])
            if x.SOURCE.is_mount():x.run(['umount',str(x.SOURCE)])
            temp=x.FSTAB.with_suffix('.storage-new');temp.write_text(new);temp.chmod(0o644);temp.replace(x.FSTAB)
            x.run(['systemctl','daemon-reload']);x.run(['mount',str(x.SOURCE)])
            if x.run(['findmnt','-n','-o','UUID','--mountpoint',str(x.SOURCE)])!=p['uuid']:raise ValueError('Unexpected mounted UUID')
            site=ROOT/'config/installed-site.json';settings=json.loads(site.read_text()) if site.exists() else {}
            settings['external_library']={'uuid':p['uuid'],'previous_uuid':p['source']['uuid']};save(site,settings,True)
            if p['mode']=='adopt' and p['configuration']=='drive':settings.pop('demo_library',None);save(site,settings,True)
            x.run([str(ROOT/'venv/bin/python'),str(ROOT/'tools/render_dashboard.py'),str(ROOT/'dataark.yaml'),'/var/www/html/index.html'])
            journal['phase']='complete';save(PRIVATE/'journal.json',journal)
            status('ready',message='Library drive selected. Existing content was retained. Choose Restore Library separately for anything missing.',uuid=p['uuid'])
            from tools.appliance_jobs import emit
            emit('configuration_published','storage')
        except Exception:
            if journal['phase']=='activating':recover()
            raise
        finally:x.resume(active,reader)
