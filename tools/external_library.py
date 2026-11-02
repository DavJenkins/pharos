#!/usr/bin/python3
"""Fixed-scope, non-formatting system-card to USB library handover.

The worker is installed root-owned; stdin accepts UUIDs and reviewed plan IDs,
never shell commands or caller-selected filesystem paths. The old image stays.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

SOURCE = Path('/mnt/storage')
STATE = Path('/var/lib/dataark/external-library')
PRIVATE = Path('/etc/dataark/external-library')
REPO = Path('/opt/dataark')
IMAGE = Path('/var/lib/dataark/demo-library.ext4')
FSTAB = Path('/etc/fstab')
MARKER = '.dataark-external-library.json'
IGNORE = {'lost+found', 'System Volume Information', '$RECYCLE.BIN'}
LOCKS = [Path('/var/lib/dataark/updates/worker.lock'),Path('/var/lib/dataark/maps/worker.lock'),Path('/var/lib/dataark/cloning/worker.lock')]

def quiesce():
    units=['dataark.service','dataark-update.timer','dataark-maps.timer']
    active=[u for u in units if subprocess.run(['systemctl','is-active','--quiet',u]).returncode==0]
    docker=subprocess.run(['docker','inspect','-f','{{.State.Running}}','kiwix-serve'],capture_output=True,text=True)
    reader=docker.returncode==0 and docker.stdout.strip()=='true'
    try:
        for u in active:run(['systemctl','stop',u])
        if reader:run(['docker','stop','kiwix-serve'])
    except Exception:
        for u in active:subprocess.run(['systemctl','start',u],capture_output=True)
        raise
    return active,reader

def resume(active,reader):
    errors=[]
    for args in ([['docker','start','kiwix-serve']] if reader else [])+[['systemctl','start',u] for u in active]:
        result=subprocess.run(args,capture_output=True,text=True)
        if result.returncode:errors.append(' '.join(args))
    if errors:raise ValueError('Library retained, but service restart needs attention: '+', '.join(errors))

def run(args):
    return subprocess.check_output(args, text=True).strip()

def save(path, value, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink(): raise ValueError('Unexpected state symlink')
    temp = path.with_suffix('.new')
    with temp.open('w') as f:
        json.dump(value, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    temp.chmod(mode); temp.replace(path)

def status(phase, **fields):
    save(STATE/'status.json', dict(phase=phase, updated=time.time(), **fields), 0o644)
    if phase in ('ready','failed') and REPO.exists():
        # Same durable collection feed polled by Home Assistant; no credentials.
        script="import sys;sys.path.insert(0,'/opt/dataark');from app.services.collection_changes import safe_record;safe_record(sys.argv[1],title='External library drive',action='external_library')"
        subprocess.run([str(REPO/'venv/bin/python'),'-c',script,'installed' if phase=='ready' else 'failed'],capture_output=True)

def uuid_ok(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-fA-F0-9-]{4,64}', value):
        raise ValueError('Invalid drive UUID')
    return value

def devices():
    data=json.loads(run(['lsblk','--json','--bytes','--paths','-o','PATH,TYPE,TRAN,FSTYPE,UUID,SIZE,MODEL,SERIAL,MOUNTPOINTS']))
    rows=[]
    for disk in data['blockdevices']:
        # Never offer the system disk or a USB disk containing the running OS.
        children=disk.get('children',[])
        mounts=[m for p in [disk]+children for m in p.get('mountpoints',[]) if m]
        if disk.get('tran')!='usb' or any(m in ('/','/boot','/boot/firmware',str(SOURCE)) for m in mounts): continue
        for part in children:
            if part.get('type')!='part' or part.get('fstype') not in ('ext4','exfat','ntfs','ntfs3') or not part.get('uuid'):continue
            uuid_ok(part['uuid'])
            rows.append(dict(uuid=part['uuid'], device=part['path'], filesystem=part['fstype'],
                             bytes=part['size'], model=(disk.get('model') or '').strip(),
                             serial=disk.get('serial') or '', mounts=[m for m in part.get('mountpoints',[]) if m]))
    return rows

def source_identity():
    if not SOURCE.is_mount() or not (SOURCE/'DEMO-LIBRARY.json').is_file():
        raise ValueError('This transition requires the active system-card library')
    loop=run(['findmnt','-n','-o','SOURCE','--mountpoint',str(SOURCE)])
    if not loop.startswith('/dev/loop') or Path(run(['losetup','-n','-O','BACK-FILE',loop])).resolve()!=IMAGE:
        raise ValueError('The active library is not the owned system-card image')
    return SOURCE.stat().st_dev

def mounted(uuid):
    row=next((d for d in devices() if d['uuid']==uuid_ok(uuid)),None)
    if not row:raise ValueError('Drive disconnected or no longer eligible')
    if len(row['mounts'])>1:raise ValueError('Drive has multiple mount points')
    if row['mounts']:target=Path(row['mounts'][0])
    else:
        target=Path('/run/dataark-external')/uuid
        target.mkdir(parents=True,exist_ok=True)
        run(['mount','-o','nodev,nosuid,noexec',row['device'],str(target)])
    if target.is_symlink() or any(p.is_symlink() for p in target.parents) or not target.is_mount():
        raise ValueError('Unsafe destination mount')
    return row,target

def files(root):
    result=[];dev=root.stat().st_dev
    for base,dirs,names in os.walk(root,followlinks=False):
        for name in dirs+names:
            p=Path(base)/name;s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or s.st_dev!=dev or not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
                raise ValueError('Library contains a link, nested mount or special file: '+str(p.relative_to(root)))
        for name in names:
            p=Path(base)/name
            if p.relative_to(root).as_posix()==MARKER:continue
            s=p.stat();result.append({'path':p.relative_to(root).as_posix(),'bytes':s.st_size,'mtime':s.st_mtime_ns})
    return sorted(result,key=lambda x:x['path'])

def plan(uuid):
    source_identity();row,target=mounted(uuid)
    entries=files(SOURCE);marker=target/MARKER
    if marker.exists():
        receipt=json.loads(marker.read_text())
        if receipt.get('uuid')!=uuid or receipt.get('generator')!='dataark-external-v1':raise ValueError('Unrelated destination metadata')
    elif any(p.name not in IGNORE for p in target.iterdir()):
        raise ValueError('Choose an empty formatted drive. Existing libraries require a separate configuration review; no files were changed.')
    required=sum(((x['bytes']+4095)//4096)*4096 for x in entries)
    # A complete copy is required. Never silently discard collections to fit.
    existing=sum(p.stat().st_size for p in target.rglob('*') if p.is_file() and not p.is_symlink())
    free=shutil.disk_usage(target).free
    if required+1024**3>free+existing:raise ValueError('Drive must fit the whole library plus 1 GiB free')
    value={'uuid':uuid,'device':row['device'],'filesystem':row['filesystem'],'serial':row['serial'],
           'source_files':entries,'bytes':sum(x['bytes'] for x in entries),'files':len(entries),'free_bytes':free}
    value['plan_id']=hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!='free_bytes'},sort_keys=True).encode()).hexdigest()
    PRIVATE.mkdir(parents=True,exist_ok=True);PRIVATE.chmod(0o700);save(PRIVATE/'plan.json',value)
    return {k:v for k,v in value.items() if k!='source_files'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(2*1024**2),b''):h.update(chunk)
    return h.hexdigest()

def copy_verified(source,target,entries,guard,progress):
    for index,item in enumerate(entries):
        guard();relative=Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe copy path')
        src=source/relative;dst=target/relative
        if src.is_symlink() or dst.is_symlink() or any(p.is_symlink() for p in dst.parents):raise ValueError('Copy path became a symlink')
        if src.stat().st_size!=item['bytes'] or src.stat().st_mtime_ns!=item['mtime']:raise ValueError('Source changed; review a fresh plan')
        dst.parent.mkdir(parents=True,exist_ok=True)
        temp=dst.with_name(dst.name+'.dataark-copying')
        if temp.is_symlink():raise ValueError('Unexpected partial-file symlink')
        with src.open('rb') as a,temp.open('wb') as b:
            for chunk in iter(lambda:a.read(2*1024**2),b''):
                guard();b.write(chunk)
            b.flush();os.fsync(b.fileno())
        if digest(temp)!=digest(src):raise ValueError('Copy verification failed: '+item['path'])
        guard();temp.replace(dst);dst.chmod(0o644)
        if os.name=='posix' and os.geteuid()==0:
            os.chown(dst,1000,1000)
            parent=dst.parent
            while parent!=target.parent:
                os.chown(parent,1000,1000)
                if parent==target:break
                parent=parent.parent
        progress(index+1,len(entries))

def fstab_external(text,uuid,filesystem):
    uuid_ok(uuid);lines=[];count=0
    for line in text.splitlines():
        f=line.split()
        if f and not line.lstrip().startswith('#') and len(f)>1 and f[1]==SOURCE.as_posix():count+=1;continue
        lines.append(line)
    if count!=1:raise ValueError('Expected exactly one current library mount entry')
    if filesystem not in ('ext4','exfat','ntfs','ntfs3'):raise ValueError('Unsupported filesystem')
    options='defaults,nofail,nodev,nosuid,x-systemd.device-timeout=10s'
    if filesystem!='ext4':options+=',uid=1000,gid=1000,umask=022'
    return '\n'.join(lines)+f'\nUUID={uuid} {SOURCE.as_posix()} {filesystem} {options} 0 0\n'

def worker():
    import fcntl
    with contextlib.ExitStack() as stack:
        for p in [PRIVATE/'worker.lock']+LOCKS:
            p.parent.mkdir(parents=True,exist_ok=True);f=stack.enter_context(p.open('a'));fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        wanted=json.loads((PRIVATE/'job.json').read_text());original=json.loads((PRIVATE/'plan.json').read_text())
        if wanted['plan_id']!=original['plan_id']:raise ValueError('Reviewed plan changed')
        source_dev=source_identity();row,target=mounted(original['uuid']);target_dev=target.stat().st_dev
        if row['device']!=original['device'] or row['serial']!=original['serial']:raise ValueError('Destination identity changed')
        def guard():
            if not SOURCE.is_mount() or SOURCE.stat().st_dev!=source_dev or not target.is_mount() or target.stat().st_dev!=target_dev:raise ValueError('A library drive disconnected')
        save(target/MARKER,{'generator':'dataark-external-v1','uuid':row['uuid'],'phase':'copying'},0o644)
        status('copying',message='Copying and verifying the system-card library.')
        # Take a quiescent snapshot. Web status may briefly reconnect while stopped.
        active,reader=quiesce()
        try:
            if files(SOURCE)!=original['source_files']:raise ValueError('Library changed since preview; review again')
            copy_verified(SOURCE,target,original['source_files'],guard,lambda n,total:status('copying',completed_files=n,total_files=total,percent=round(n*100/max(1,total)),message='Copying and verifying files.'))
            guard();save(target/MARKER,{'generator':'dataark-external-v1','uuid':row['uuid'],'phase':'verified'},0o644)
            status('verified',message='Copy verified. Choose Use this drive to switch; the system-card library is still active.',plan_id=original['plan_id'])
        finally:
            resume(active,reader)

def switch():
    import fcntl
    with contextlib.ExitStack() as stack:
        for path in [PRIVATE/'worker.lock']+LOCKS:
            path.parent.mkdir(parents=True,exist_ok=True);f=stack.enter_context(path.open('a'));fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=json.loads((PRIVATE/'plan.json').read_text());s=json.loads((STATE/'status.json').read_text())
        if s['phase']!='verified' or s.get('plan_id')!=p['plan_id']:raise ValueError('Finish verification first')
        source_identity();row,target=mounted(p['uuid'])
        if files(SOURCE)!=p['source_files']:raise ValueError('Source changed since verification; copy again')
        for item in p['source_files']:
            if digest(SOURCE/item['path'])!=digest(target/item['path']):raise ValueError('Verified copy changed; copy again')
        old=FSTAB.read_text();new=fstab_external(old,row['uuid'],row['filesystem']);save(PRIVATE/'rollback.json',{'fstab':old,'uuid':row['uuid']})
        installed=REPO/'config/installed-site.json';old_site=installed.read_bytes()
        active,reader=quiesce()
        try:
            status('switching',message='Switching library storage; reconnecting…')
            # Recheck after quiescing, before the mount handover.
            if files(SOURCE)!=p['source_files']:raise ValueError('Library changed; repeat copy')
            run(['umount',str(target)]);run(['umount',str(SOURCE)])
            temp=FSTAB.with_suffix('.dataark-new');temp.write_text(new);temp.chmod(0o644);temp.replace(FSTAB)
            run(['systemctl','daemon-reload']);run(['mount',str(SOURCE)])
            actual=run(['findmnt','-n','-o','UUID','--mountpoint',str(SOURCE)])
            if actual!=p['uuid']:raise ValueError('Wrong external volume mounted')
            # Keep demo sample registrations; change only its storage label.
            site=json.loads(old_site);site['external_library']={'uuid':p['uuid'],'previous_image':str(IMAGE)};save(installed,site,0o644)
            run([str(REPO/'venv/bin/python'),str(REPO/'tools/render_dashboard.py'),str(REPO/'dataark.yaml'),'/var/www/html/index.html'])
            status('ready',message='External library active. The system-card copy is retained.',uuid=p['uuid'])
        except Exception:
            FSTAB.write_text(old);installed.write_bytes(old_site)
            subprocess.run(['umount',str(SOURCE)],capture_output=True);run(['systemctl','daemon-reload']);run(['mount',str(SOURCE)])
            raise
        finally:
            resume(active,reader)

def main():
    if os.geteuid()!=0:raise ValueError('Root helper required')
    if sys.argv[1:]==['--worker']:
        try:worker()
        except Exception as e:status('failed',message=str(e));raise
        return
    if sys.argv[1:]==['--switch']:
        try:switch()
        except Exception as e:status('failed',message=str(e));raise
        return
    if sys.argv[1:]:raise ValueError('No helper arguments accepted')
    data=json.loads(sys.stdin.buffer.read(2049))
    if not isinstance(data,dict):raise ValueError('JSON object required')
    import fcntl
    request_lock=(PRIVATE/'request.lock').open('a');fcntl.flock(request_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for unit in ['dataark-external-copy.service','dataark-external-switch.service']:
        if run(['systemctl','show','-p','ActiveState','--value',unit]) in ('active','activating'):
            raise ValueError('A transition is already running; check status')
    if data=={'action':'drives'}:value={'drives':devices(),'system_card_active':SOURCE.is_mount() and (SOURCE/'DEMO-LIBRARY.json').exists()}
    elif set(data)=={'action','uuid'} and data['action']=='plan':value=plan(data['uuid'])
    elif set(data)=={'action','plan_id'} and data['action'] in ('copy','switch'):
        p=json.loads((PRIVATE/'plan.json').read_text())
        if data['plan_id']!=p['plan_id']:raise ValueError('Review the current plan')
        unit='dataark-external-copy.service' if data['action']=='copy' else 'dataark-external-switch.service'
        for other in ['dataark-external-copy.service','dataark-external-switch.service']:
            if run(['systemctl','show','-p','ActiveState','--value',other]) in ('active','activating'):raise ValueError('A transition is already running')
        save(PRIVATE/'job.json',{'plan_id':p['plan_id']});status('queued',message='Library transition queued.')
        run(['systemctl','start','--no-block',unit]);value={'queued':True}
    else:raise ValueError('Invalid external-library request')
    print(json.dumps({'ok':True,**value}))

if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
