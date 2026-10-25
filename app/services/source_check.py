"""One bounded source availability sweep at a time, without downloading archives."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import threading
import time
from app.services.manifest import load_manifest, atomic_write, ManifestError
from app.services.upstream import check_assets, asset_state, source_urls

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'dataark.yaml'
CACHE=ROOT/'.cache/manifest-upstream.json'
LOCK_FILE=ROOT/'.cache/source-check.lock'
LOCK=threading.RLock()
STATE={'state':'idle','completed':0,'total':0,'message':''}
LAST_REQUEST=0.0

class CheckError(Exception):
    def __init__(self,status,message):self.status,self.message=status,message

def current():
    with LOCK:
        result=dict(STATE)
        result['retry_after']=max(0,int(60-(time.monotonic()-LAST_REQUEST)))
    if result['state']!='checking':
        try:
            cached=json.loads(CACHE.read_text())
            data=load_manifest(MANIFEST)
            result['assets']={a['id']:asset_state(a,cached.get('assets',{})) for a in data.get('assets',[]) if source_urls(a) and not a.get('removed')}
            result['checked_at']=cached.get('batch_finished_at')
        except (OSError,ValueError,TypeError,AttributeError,ManifestError):pass
    return result

def start():
    global LAST_REQUEST
    with LOCK:
        if STATE['state']=='checking':return current()
        if time.monotonic()-LAST_REQUEST<60:
            raise CheckError(429,'Please wait a minute between source checks.')
        LOCK_FILE.parent.mkdir(exist_ok=True)
        file=LOCK_FILE.open('a')
        try:fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            file.close();raise CheckError(409,'Another source check is already running.') from None
        LAST_REQUEST=time.monotonic()
        STATE.update(state='checking',completed=0,total=0,message='Starting source check…')
        try:threading.Thread(target=run,args=(file,),daemon=True,name='dataark-source-check').start()
        except Exception:
            file.close();STATE.update(state='failed',message='Unable to start source check.');raise
        return current()

def run(file):
    try:
        data=load_manifest(MANIFEST)
        assets=[a for a in data.get('assets',[]) if not a.get('removed') and source_urls(a)]
        if len(assets)>2000:raise ValueError('Too many sources for one check. Ask the caretaker to review the catalogue.')
        def progress(done,total):
            with LOCK:STATE.update(completed=done,total=total,message=f'Checking {done} / {total}…')
        result=check_assets(assets,progress=progress)
        atomic_write(CACHE,json.dumps(result,indent=2).encode())
        counts={state:sum(a['status']==state for a in result['assets'].values()) for state in ['available','unavailable','unknown']}
        with LOCK:STATE.update(state='complete',completed=len(assets),total=len(assets),message=f"{len(assets)} checked: {counts['unavailable']} unavailable, {counts['unknown']} unknown.")
    except Exception:
        with LOCK:STATE.update(state='failed',message='Source check failed. Previous results were kept; ask the caretaker to check the service log.')
        import logging
        logging.getLogger(__name__).exception('Source availability check failed')
    finally:
        file.close()
