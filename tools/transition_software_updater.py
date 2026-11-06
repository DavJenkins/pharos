#!/usr/bin/python3
"""Explicit, root-authorized transition of the updater verifier; never enrolls a new baseline."""
import argparse,hashlib,json,os,subprocess,tempfile,time
from pathlib import Path

def atomic(path,raw,mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
        temp=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
    try:
        temp.chmod(mode);os.replace(temp,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:temp.unlink(missing_ok=True)

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate manifest key')
        result[key]=value
    return result

def sha(raw):return hashlib.sha256(raw).hexdigest()
def transition(engine,manifest,signature,root=Path('/')):
    if os.geteuid()!=0:raise ValueError('Root authorization required')
    raw=manifest.read_bytes();code=engine.read_bytes();sig=signature.read_bytes()
    if len(raw)>4096 or len(code)>256*1024 or len(sig)>1024:raise ValueError('Transition input too large')
    value=json.loads(raw,object_pairs_hook=unique)
    if set(value)!={'schema','type','from_engine_sha256','to_engine_sha256','receipt_sha256'} or value['schema']!=1 or value['type']!='updater-v2-transition':raise ValueError('Invalid transition manifest')
    state=root/'var/lib/dataark-software-updates';target=root/'usr/local/libexec/software_update.py';receipt=state/'installed.json'
    for path in (state,target,receipt):
        if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Symlink in transition destination')
    if sha(target.read_bytes())!=value['from_engine_sha256'] or sha(receipt.read_bytes())!=value['receipt_sha256'] or sha(code)!=value['to_engine_sha256']:raise ValueError('Transition baseline changed')
    compile(code,'software_update.py','exec')
    import fcntl
    with (state/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name in ('queued.json',):
            if (state/name).exists():raise ValueError('Software update queued')
        journal=state/'transaction.json'
        if journal.exists() and json.loads(journal.read_text()).get('state') in ('preparing','applying','checking','rolling_back','rollback_pending_health'):raise ValueError('Software transaction unresolved')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'manifest').write_bytes(raw);(folder/'signature').write_bytes(sig)
            trusted=False
            for key in (root/'etc/dataark/software-update-keys').glob('*.pem'):
                st=key.stat()
                if key.is_symlink() or st.st_uid!=0 or st.st_mode&0o022:continue
                r=subprocess.run(['/usr/bin/openssl','pkeyutl','-verify','-pubin','-inkey',str(key),'-rawin','-in',str(folder/'manifest'),'-sigfile',str(folder/'signature')],capture_output=True,timeout=5)
                if r.returncode==0:trusted=True;break
            if not trusted:raise ValueError('Transition signature is not trusted')
        # Recheck both immutable inputs while holding the updater lock.
        old=target.read_bytes();old_receipt=receipt.read_bytes()
        if sha(old)!=value['from_engine_sha256'] or sha(old_receipt)!=value['receipt_sha256']:raise ValueError('Transition baseline changed')
        backup=state/('verifier-transition-'+str(time.time_ns()));backup.mkdir(mode=0o700)
        atomic(backup/'software_update.py',old);atomic(backup/'installed.json',old_receipt)
        atomic(backup/'manifest.json',raw);atomic(backup/'manifest.sig',sig)
        try:
            atomic(target,code,0o644);os.chown(target,0,0)
            result=subprocess.run(['/usr/bin/python3','-I','-c','import importlib.util; p='+repr(str(target))+'; s=importlib.util.spec_from_file_location("transition_verifier",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.allowed("helpers/dataark-library")'],capture_output=True,timeout=10)
            if result.returncode:raise ValueError('New verifier failed its isolated import check')
            if receipt.read_bytes()!=old_receipt:raise ValueError('Installed receipt changed unexpectedly')
        except BaseException:
            atomic(target,old,0o644);os.chown(target,0,0);raise
        atomic(backup/'result.json',json.dumps({'state':'completed','baseline_preserved':True,'new_engine_sha256':sha(code)}).encode())
        return {'state':'completed','baseline_preserved':True,'backup':str(backup)}

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','manifest','signature'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(transition(a.engine,a.manifest,a.signature)))
