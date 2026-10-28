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
            c.write_json(c.STATE/'status.json',{'state':'error','message':'The updater is busy. Wait until it finishes, then save again.'})
            from app.services.collection_changes import safe_record
            safe_record('configuration_failed', action='configuration', error_type='UpdaterBusy')
            return
        job=json.loads(pending.read_text());raw,live=c.current();profile=ROOT/'config/content/public-manifest.yaml'
        previous=profile.read_bytes() if profile.exists() else None
        applied=False
        project_root=ROOT/'config/library'
        old_project={}
        old_layout=None
        try:
            if c.revision(raw)!=job['revision']:raise ValueError('Configuration changed before publication. Reload it and retry.')
            data=c.checked(job['text'],live)
            if job.get('project_token'):
                if c.project.fingerprint(project_root)!=job['project_token']:raise ValueError('Modular files changed before publication.')
                c.project.assert_base(project_root,c.public(live))
            else:c.project.ensure_clean(project_root)
            old_project=c.project.disk_files(project_root)
            index=project_root/'.layout.json';old_layout=index.read_bytes() if index.exists() else None
            backup=BACKUPS;backup.mkdir(mode=0o700,parents=True,exist_ok=True)
            atomic_write(backup/(job['id']+'.yaml'),raw);(backup/(job['id']+'.yaml')).chmod(0o600)
            if old_project:
                saved=backup/(job['id']+'.project.json')
                atomic_write(saved,json.dumps({'files':old_project,'layout':old_layout.decode() if old_layout else None},ensure_ascii=False).encode());saved.chmod(0o600)
            folder=c.STATE/'history';folder.mkdir(exist_ok=True);folder.chmod(0o700);os.chown(folder,1000,1000)
            c.write_json(folder/(job['id']+'.json'),{'saved_at':c.stamp(),'text':c.dump(c.public(live))})
            c.write_json(c.STATE/'status.json',{'id':job['id'],'state':'publishing','message':'Publishing configuration…','updated_at':c.stamp()})
            applied=True
            atomic_write(ROOT/'dataark.yaml',c.dump(data).encode());os.chown(ROOT/'dataark.yaml',1000,1000)
            atomic_write(profile,job['text'].encode());os.chown(profile,1000,1000)
            edit=job.get('source_edit');overrides={edit['file']:edit['text']} if edit else None
            if job.get('project_token'):
                assembled,_=c.project.assemble(old_project.__getitem__)
                if c.public(assembled)!=c.public(data):raise ValueError('Modular source and reviewed publication differ.')
                c.project.write_files(project_root,old_project)
            else:c.project.write(project_root,c.public(data),overrides)
            subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],cwd=ROOT,check=True,timeout=180)
            # Mirror the desired recipe without replacing it from the current disk inventory.
            from tools.content_profile import read,mirror
            if CONTENT_ROOT.is_mount():
                folder=ROOT/'config/content';mirror(read(folder/'content.yaml'),folder,CONTENT_ROOT/'DATA-ARK-CONFIG')
            with (c.STATE/'editor.lock').open('a') as editor_lock:
                fcntl.flock(editor_lock,fcntl.LOCK_EX)
                pending.unlink(missing_ok=True)
                c.write_json(c.STATE/'status.json',{'id':job['id'],'state':'ready','message':'Configuration saved and published.','updated_at':c.stamp()})
                from app.services.collection_changes import safe_record
                safe_record('configuration_published', operation_id=job['id'], action='configuration')
        except Exception as error:
            outcome='No new configuration was applied.'
            if applied:
                try:
                    atomic_write(ROOT/'dataark.yaml',raw);os.chown(ROOT/'dataark.yaml',1000,1000)
                    if previous is not None:atomic_write(profile,previous);os.chown(profile,1000,1000)
                    else:profile.unlink(missing_ok=True)
                    if old_project:
                        c.project.write_files(project_root,old_project)
                        if old_layout is not None:
                            index=project_root/'.layout.json';atomic_write(index,old_layout);index.chmod(0o644);os.chown(index,1000,1000)
                    else:c.project.write(project_root,c.public(live))
                    result=subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],cwd=ROOT,timeout=180,check=False)
                    outcome='Previous configuration restored.' if result.returncode==0 else 'Previous configuration restored on disk; webpage publication needs attention.'
                    if CONTENT_ROOT.is_mount():
                        from tools.content_profile import read,mirror
                        folder=ROOT/'config/content';mirror(read(folder/'content.yaml'),folder,CONTENT_ROOT/'DATA-ARK-CONFIG')
                except Exception:
                    outcome='Automatic recovery needs attention. The previous configuration is saved in the backup/history.'
            c.write_json(c.STATE/'status.json',{'id':job.get('id'),'state':'error','message':outcome+' '+str(error),'updated_at':c.stamp()})
            from app.services.collection_changes import safe_record
            safe_record('configuration_failed', operation_id=job.get('id',''), action='configuration', error_type=type(error).__name__)

if __name__=='__main__':main()
