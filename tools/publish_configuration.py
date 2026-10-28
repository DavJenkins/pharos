#!/usr/bin/env python3
"""Publish one validated content configuration, rolling back on failure."""
import fcntl,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services import configuration as c
from app.services.manifest import atomic_write
WORKER_LOCK=Path("/var/lib/dataark/updates/worker.lock")
BACKUPS=Path("/var/backups/dataark-configuration")
CONTENT_ROOT=Path("/mnt/storage")

def main():
    pending=c.STATE/'pending.json'
    if not pending.exists():return
    with WORKER_LOCK.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            c.write_json(c.STATE/'status.json',{'state':'error','message':'The updater is busy. Wait until it finishes, then save again.'});return
        job=json.loads(pending.read_text());raw,live=c.current();profile=ROOT/'config/content/public-manifest.yaml'
        previous=profile.read_bytes() if profile.exists() else None
        applied=False
        try:
            if c.revision(raw)!=job['revision']:raise ValueError('Configuration changed before publication. Reload it and retry.')
            data=c.checked(job['text'],live)
            backup=BACKUPS;backup.mkdir(mode=0o700,parents=True,exist_ok=True)
            atomic_write(backup/(job['id']+'.yaml'),raw);(backup/(job['id']+'.yaml')).chmod(0o600)
            folder=c.STATE/'history';folder.mkdir(exist_ok=True);folder.chmod(0o700);os.chown(folder,1000,1000)
            c.write_json(folder/(job['id']+'.json'),{'saved_at':c.stamp(),'text':c.dump(c.public(live))})
            c.write_json(c.STATE/'status.json',{'id':job['id'],'state':'publishing','message':'Publishing configuration…','updated_at':c.stamp()})
            applied=True
            atomic_write(ROOT/'dataark.yaml',c.dump(data).encode());os.chown(ROOT/'dataark.yaml',1000,1000)
            atomic_write(profile,job['text'].encode());os.chown(profile,1000,1000)
            subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],cwd=ROOT,check=True,timeout=180)
            # Mirror the desired recipe without replacing it from the current disk inventory.
            from tools.content_profile import read,mirror
            if CONTENT_ROOT.is_mount():
                folder=ROOT/'config/content';mirror(read(folder/'content.yaml'),folder,CONTENT_ROOT/'DATA-ARK-CONFIG')
            with (c.STATE/'editor.lock').open('a') as editor_lock:
                fcntl.flock(editor_lock,fcntl.LOCK_EX)
                pending.unlink(missing_ok=True)
                c.write_json(c.STATE/'status.json',{'id':job['id'],'state':'ready','message':'Configuration saved and published.','updated_at':c.stamp()})
        except Exception as error:
            outcome='No new configuration was applied.'
            if applied:
                try:
                    atomic_write(ROOT/'dataark.yaml',raw);os.chown(ROOT/'dataark.yaml',1000,1000)
                    if previous is not None:atomic_write(profile,previous);os.chown(profile,1000,1000)
                    else:profile.unlink(missing_ok=True)
                    result=subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],cwd=ROOT,timeout=180,check=False)
                    outcome='Previous configuration restored.' if result.returncode==0 else 'Previous configuration restored on disk; webpage publication needs attention.'
                    if CONTENT_ROOT.is_mount():
                        from tools.content_profile import read,mirror
                        folder=ROOT/'config/content';mirror(read(folder/'content.yaml'),folder,CONTENT_ROOT/'DATA-ARK-CONFIG')
                except Exception:
                    outcome='Automatic recovery needs attention. The previous configuration is saved in the backup/history.'
            c.write_json(c.STATE/'status.json',{'id':job.get('id'),'state':'error','message':outcome+' '+str(error),'updated_at':c.stamp()})

if __name__=='__main__':main()
