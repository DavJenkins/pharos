#!/opt/dataark/venv/bin/python
"""Fixed caretaker operations for browser-driven cloning and restoration.

Root-owned installation. No caller command, executable, path, profile or unit
name is accepted. Existing copy and recovery engines retain their own locks.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT=Path('/opt/dataark')
PRIVATE=Path('/etc/dataark/appliance-jobs')
if str(ROOT) not in sys.path:sys.path.append(str(ROOT))

def active(unit):
    result=subprocess.run(['systemctl','show','-p','ActiveState','-p','Job',unit],capture_output=True,text=True,check=True)
    fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    return fields.get('ActiveState') in ('active','activating','reloading','deactivating') or bool(fields.get('Job'))

def start(unit):subprocess.run(['systemctl','start','--no-block',unit],check=True)

def emit(kind,action):
    from app.services.collection_changes import safe_record
    safe_record(kind,title={'clone':'Make another Ark','recipient':'Prepare a recipient','storage':'Library storage and recovery','card':'Prepare a system card'}.get(action,'Restore Library'),action=action)

def save(path,value):
    from tools.clone_drive import save as atomic
    atomic(path,value);path.chmod(0o600)

def validate(data):
    if not isinstance(data,dict):raise ValueError('JSON object required')
    fields={'discover':set(),'clone_preview':{'uuid','mode'},'clone_start':{'plan_id'},'clone_pause':set(),'clone_eject':{'uuid'},
            'restore_start':{'preset','plan_id','replace_finished'},'restore_resume':set(),
            'restore_pause':set(),'restore_cancel':set(),'recipient_preview':set(),
            'recipient_prepare':{'plan_id','personal_reviewed'},'recipient_sheet':set(),
            'storage_plan':{'uuid','mode','configuration','copy_existing'},'storage_apply':{'plan_id'},'storage_reconnect':set(),
            'card_package':{'library_gib','country'}}
    action=data.get('action')
    if action not in fields or set(data)!={'action'}|fields[action]:raise ValueError('Invalid operation or fields')
    if action in ('clone_preview','clone_eject','storage_plan'):
        if not isinstance(data['uuid'],str) or not re.fullmatch(r'[A-Fa-f0-9-]{4,64}',data['uuid']):raise ValueError('Invalid drive UUID')
    if action=='clone_preview':
        if data['mode'] not in ('config','fit','populated'):raise ValueError('Invalid copy mode')
    if 'plan_id' in data and (not isinstance(data['plan_id'],str) or not re.fullmatch('[a-f0-9]{64}',data['plan_id'])):raise ValueError('Invalid plan ID')
    if action=='restore_start':
        if data['preset'] not in ('none','minimal','recommended','full') or type(data['replace_finished']) is not bool:raise ValueError('Invalid restoration choice')
    if action=='recipient_prepare' and data['personal_reviewed'] is not True:raise ValueError('Review personal files and owner settings before preparing a recipient')
    if action=='storage_plan' and (data['mode'] not in ('adopt','replace') or data['configuration'] not in ('keep','drive') or type(data['copy_existing']) is not bool):raise ValueError('Invalid storage selection')
    if action=='card_package':
        from tools.ready_card import validate as validate_card
        validate_card(data['library_gib'],data['country'])
    return action

def storage_module():
    # Import the already reviewed, root-owned discovery/mount implementation.
    import importlib.machinery,importlib.util
    loader=importlib.machinery.SourceFileLoader('dataark_storage','/usr/local/libexec/dataark-external-library')
    spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module

def archive_finished(queue):
    directory=queue.STATE
    current=json.loads((directory/'queue.json').read_text())
    if current['status'] not in ('complete','cancelled'):raise ValueError('Finish or cancel the existing queue before replacing it')
    destination=directory.parent/'recovery-history'/(str(time.time_ns())+'-'+uuid.uuid4().hex[:8]);destination.mkdir(parents=True,exist_ok=False)
    for path in directory.iterdir():
        if path.name=='queue.lock':continue
        if path.is_symlink():raise ValueError('Unexpected queue symlink')
    for path in list(directory.iterdir()):
        if path.name!='queue.lock':path.rename(destination/path.name)

def dispatch(data):
    action=validate(data)
    if action=='discover':return {'drives':storage_module().devices()}
    if action=='card_package':
        from tools import ready_card
        if active('dataark-card-package.service'):raise ValueError('Card package is already being built')
        save(PRIVATE/'card-job.json',{'library_gib':data['library_gib'],'country':data['country']});ready_card.status('queued',message='Card preparation package queued. No physical card is being written.')
        emit('queued','card');start('dataark-card-package.service');return {'queued':True}
    if action.startswith('recipient_'):
        from tools import prepare_recipient as recipient
        if action=='recipient_sheet':return {'html':recipient.welcome_sheet()}
        inspection=recipient.inspection()
        if action=='recipient_preview':return inspection
        if data['plan_id']!=inspection['plan_id'] or not inspection['eligible']:raise ValueError('Preparation requirements changed; inspect again')
        recipient.arm();emit('configuration_published','recipient')
        return {'html':recipient.welcome_sheet(),'message':'Prepared for its next owner. Save the private welcome sheet, then shut down. The next boot changes identities and starts recipient setup.'}
    if action.startswith('storage_'):
        from tools import storage_workflows as storage
        if active('dataark-storage.service'):raise ValueError('A storage operation is already running')
        if action=='storage_reconnect':return storage.reconnect()
        if action=='storage_plan':return storage.plan(data['uuid'],data['mode'],data['configuration'],data['copy_existing'])
        p=json.loads((storage.PRIVATE/'plan.json').read_text())
        if p['plan_id']!=data['plan_id']:raise ValueError('Storage plan changed; review again')
        storage.save(storage.PRIVATE/'job.json',p);storage.status('queued',message='Storage verification and activation queued.')
        emit('queued','storage');start('dataark-storage.service');return {'queued':True}
    from tools import clone_drive as clone,recovery_queue as queue
    if action.startswith('clone_'):
        if action=='clone_pause':
            if not active('dataark-clone.service'):raise ValueError('No browser copy is running')
            subprocess.run(['systemctl','stop','dataark-clone.service'],check=True)
            emit('waiting','clone');return {'message':'Copy stopped. Verified files and partial data are retained; preview this drive again to resume.'}
        if active('dataark-clone.service'):raise ValueError('A copy is already running; check progress')
        if action=='clone_eject':
            state=clone.status()
            if state.get('state')!='ready' or state.get('target_uuid')!=data['uuid']:raise ValueError('Only the completed copy can be ejected here')
            candidates=[d for d in storage_module().devices() if d['uuid']==data['uuid']]
            if len(candidates)!=1:raise ValueError('Drive UUID is missing or ambiguous; inspect attached drives')
            row=candidates[0]
            if not row or row['mounts']!=[state['target']]:raise ValueError('Destination mount changed; inspect the drive before ejecting')
            marker=json.loads((Path(state['target'])/'.dataark-clone/state.json').read_text())
            if marker.get('state')!='ready' or marker.get('plan_id')!=state['plan_id']:raise ValueError('Completed copy metadata changed')
            subprocess.run(['umount',state['target']],check=True)
            clone.save(clone.STATUS/'status.json',{**state,'state':'ejected'})
            return {'message':'Drive unmounted. It is safe to disconnect.'}
        if action=='clone_preview':
            storage=storage_module()
            if len([d for d in storage.devices() if d['uuid']==data['uuid']])!=1:raise ValueError('Drive UUID is missing or ambiguous; inspect attached drives')
            _,target=storage.mounted(data['uuid'])
            plan=clone.build_plan(target,data['mode']);save(PRIVATE/'clone-plan.json',plan)
            return {**clone.summary(plan),'resuming':clone.journal_path(target).exists()}
        plan=json.loads((PRIVATE/'clone-plan.json').read_text())
        current=clone.build_plan(plan['target']['path'],plan['mode'])
        if data['plan_id']!=plan['plan_id'] or current['plan_id']!=data['plan_id'] or not current['fits']:
            raise ValueError('The copy plan changed or does not fit; preview again')
        # A later preview must never substitute an unapproved worker plan.
        save(PRIVATE/'clone-job.json',current)
        clone.save(clone.STATUS/'status.json',{'state':'queued','files_total':sum(len(u['files']) for u in current['selected']),'files_complete':0})
        emit('queued','clone');start('dataark-clone.service');return {'queued':True}
    running=active('dataark-recovery.service')
    if action in ('restore_pause','restore_cancel'):
        control='pause' if action=='restore_pause' else 'cancel'
        if not (queue.STATE/'queue.json').exists():raise ValueError('No restoration queue exists')
        queue.control(control)
        if running:subprocess.run(['systemctl','stop','dataark-recovery.service'],check=True)
        lock=queue.lock(queue.STATE/'queue.lock')
        try:
            q=json.loads((queue.STATE/'queue.json').read_text())
            if q['status']!='complete':queue.transition(q,queue.STATE,'paused' if control=='pause' else 'cancelled')
        finally:lock.close()
        emit('cancelled' if control=='cancel' else 'waiting','restore')
        return {'requested':control,'message':'Queue '+('paused' if control=='pause' else 'cancelled')+'. Verified content and partial files are retained.'}
    if running:raise ValueError('Restoration is already running')
    if action=='restore_start':
        plan=queue.build_plan(ROOT/'config/content/content.yaml',data['preset'])
        if plan['plan_id']!=data['plan_id'] or not plan['capacity']['fits']:raise ValueError('Plan changed, sizes are unknown or capacity is insufficient; review again')
        if not Path('/mnt/storage').is_mount():raise ValueError('Connect the library drive first')
        lock=queue.lock(queue.STATE/'queue.lock')
        try:
            if (queue.STATE/'queue.json').exists():
                if not data['replace_finished']:raise ValueError('A queue exists; resume it, or explicitly keep its history and start a new selection')
                archive_finished(queue)
            queue.create(plan,data['plan_id'])
        finally:lock.close()
    else:
        q=json.loads((queue.STATE/'queue.json').read_text())
        if q['profile_sha256']!=queue.fingerprint(q['profile'],q['policy']):raise ValueError('Saved configuration changed; a fresh restoration plan is required')
        if q['status']=='complete':raise ValueError('This queue is already complete')
        if not Path('/mnt/storage').is_mount():raise ValueError('Connect the library drive first')
    emit('queued','restore');start('dataark-recovery.service');return {'queued':True}

def clone_worker():
    from tools import clone_drive as clone
    try:
        plan=json.loads((PRIVATE/'clone-job.json').read_text());current=clone.build_plan(plan['target']['path'],plan['mode'])
        if current['plan_id']!=plan['plan_id']:raise ValueError('Reviewed copy plan changed; preview again')
        clone.apply(current,plan['plan_id'],resume=clone.journal_path(plan['target']['path']).exists());emit('installed','clone')
    except Exception as e:
        clone.save(clone.STATUS/'status.json',{'state':'interrupted','error':str(e),'updated_at':time.time()});emit('failed','clone');raise

def main():
    if os.geteuid()!=0:raise ValueError('Root helper required')
    if sys.argv[1:]==['--clone-worker']:clone_worker();return
    if sys.argv[1:]==['--storage-worker']:
        from tools import storage_workflows as storage
        try:storage.worker()
        except Exception as e:storage.status('failed',message=str(e));emit('failed','storage');raise
        return
    if sys.argv[1:]==['--storage-recover']:
        from tools.storage_workflows import recover
        recover();return
    if sys.argv[1:]==['--card-package']:
        from tools.ready_card import worker
        worker();return
    if sys.argv[1:]==['--restore-report']:
        from tools.recovery_queue import snapshot,STATE
        state=snapshot()['status']
        try:control=json.loads((STATE/'control.json').read_text()).get('action')
        except (OSError,ValueError):control=None
        if state!='complete' and control in ('pause','cancel'):state='paused' if control=='pause' else 'cancelled'
        emit('installed' if state=='complete' else 'waiting' if state=='paused' else 'cancelled' if state=='cancelled' else 'failed','restore');return
    if sys.argv[1:]:raise ValueError('No caller arguments allowed')
    import fcntl
    with (PRIVATE/'request.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        raw=sys.stdin.buffer.read(4097)
        if len(raw)>4096:raise ValueError('Request too large')
        value=dispatch(json.loads(raw));print(json.dumps({'ok':True,**value}))

if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
