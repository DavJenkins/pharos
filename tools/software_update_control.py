#!/usr/bin/python3
"""Root-owned, fixed-scope software updater boundary. Package hooks are forbidden."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from software_update import Updater,save

INBOX=Path('/var/lib/dataark/software-inbox')

def status(updater):
    value=updater.journal();receipt=updater.receipt()
    try:
        queued=json.loads((updater.state/'queued.json').read_text())
        if value.get('id')!=queued['id']:value={**value,'state':'queued'}
    except FileNotFoundError:pass
    return {'ok':True,'configured':bool(list(updater.trust.glob('*.pem'))),'state':value['state'],
        'release':value.get('release'),'error':value.get('error'),'revision':receipt['revision'],'profile':receipt['profile'],
        'sequence':receipt['sequence'],'installed_release':receipt.get('release'),'installed_at':receipt.get('installed_at'),
        'installation_supported':True,'operation_id':value.get('id')}

def control(data):
    if not isinstance(data,dict) or data.get('action') not in ('status','stage','apply'):raise ValueError('Invalid updater operation')
    action=data['action']
    if set(data)!=({'action'} if action=='status' else {'action','id'}):raise ValueError('Invalid operation fields')
    updater=Updater()
    if action=='status':return status(updater)
    identifier=data['id']
    if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier):raise ValueError('Invalid operation ID')
    if action=='stage':
        package=INBOX/(identifier+'.tar.gz')
        try:return {'ok':True,**updater.stage(package)}
        finally:package.unlink(missing_ok=True)
    updater.validate(updater.stage_path(identifier));updater.runtime.preflight()
    with updater.lock():
        if updater.journal()['state'] in ('preparing','applying','checking','rolling_back','rollback_pending_health'):raise ValueError('Another update or recovery needs attention')
        queue=updater.state/'queued.json'
        if queue.exists():raise ValueError('An update is already queued')
        save(queue,{'id':identifier})
        try:subprocess.run(['/usr/bin/systemctl','start','--no-block','dataark-software-update.service'],check=True,capture_output=True,timeout=5)
        except Exception:queue.unlink(missing_ok=True);raise
    return {'ok':True,'state':'queued','id':identifier}

def main():
    if os.geteuid()!=0:raise ValueError('Root required')
    os.umask(0o077)
    if len(sys.argv)==2 and sys.argv[1] in ('--worker','--recover','--boot-recover','--verify-recovery'):
        updater=Updater();action=sys.argv[1]
        active=Path('/run/dataark-software-update-active')
        if action=='--worker':
            queue=updater.state/'queued.json';identifier=json.loads(queue.read_text())['id']
            active.write_text(str(os.getpid()));active.chmod(0o600)
            try:result=updater.apply(identifier)
            finally:queue.unlink(missing_ok=True);active.unlink(missing_ok=True)
        elif action=='--verify-recovery':result=updater.verify_recovery()
        else:
            if action=='--recover':active.write_text(str(os.getpid()));active.chmod(0o600)
            try:
                result=updater.recover(boot=action=='--boot-recover')
                (updater.state/'queued.json').unlink(missing_ok=True)
            finally:
                if action=='--recover':active.unlink(missing_ok=True)
        print(json.dumps(result));return
    if len(sys.argv)!=1:raise ValueError('No command-line arguments permitted')
    raw=sys.stdin.buffer.read(2049)
    if len(raw)>2048:raise ValueError('Request too large')
    print(json.dumps(control(json.loads(raw))))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:300]}));sys.exit(1)
