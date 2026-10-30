#!/usr/bin/python3
"""Signed, dependency/schema-preserving software transactions. No package hooks."""
import argparse
from datetime import datetime,timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import uuid
from urllib.request import urlopen

MAX_BYTES=256*1024*1024
SHA=re.compile(r'[0-9a-f]{64}')
REV=re.compile(r'[0-9a-f]{40}')
ID=re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

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

def save(path,value):atomic(path,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate manifest key')
        result[key]=value
    return result

def allowed(name):
    if not isinstance(name,str) or '\\' in name or len(name)>240:return False
    p=PurePosixPath(name)
    if p.is_absolute() or any(v in ('','.','..') for v in name.split('/')):return False
    parts=p.parts
    if len(parts)<3:return False
    if parts[0]=='source':
        return ((parts[1]=='app' and (p.suffix=='.py' or len(parts)>4 and parts[2:4] in (('static','config'),) and p.suffix=='.html' or len(parts)>5 and parts[2:5] in (('static','assets','js'),('static','assets','css')) and p.suffix in ('.js','.css')))
                or parts[1]=='docs' and p.suffix in ('.md','.json'))
    return parts[0]=='web' and ((parts[1]=='config' and p.suffix=='.html') or parts[1]=='assets' and parts[2] in ('js','css') and p.suffix in ('.js','.css') or parts[1]=='docs' and p.suffix in ('.html','.json'))


class Runtime:
    def system(self,*args):return subprocess.run(['/usr/bin/systemctl',*args],check=True,capture_output=True,timeout=45)
    def preflight(self):
        for unit in ('dataark-update.service','dataark-configuration-publish.service','dataark-library-operation.service'):
            result=subprocess.run(['/usr/bin/systemctl','is-active',unit],capture_output=True,text=True,timeout=3)
            if result.stdout.strip() in ('active','activating','reloading'):raise ValueError('Wait for active maintenance to finish: '+unit)
        database=Path('/var/lib/dataark/bugout/state.sqlite')
        if database.exists():
            try:
                with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True,timeout=2) as db:
                    if db.execute("SELECT 1 FROM operations WHERE state IN ('queued','running') LIMIT 1").fetchone():raise ValueError('Wait for the active bug-out operation to finish')
            except sqlite3.Error:raise ValueError('Cannot verify bug-out activity') from None
    def stop(self):self.system('stop','dataark.service')
    def start(self):self.system('start','dataark.service')
    def healthy(self):
        for _ in range(15):
            try:
                with urlopen('http://127.0.0.1/api/',timeout=2) as response:
                    if json.load(response).get('status')=='running':
                        with urlopen('http://127.0.0.1/',timeout=2) as page:
                            if page.status==200:return True
            except (OSError,ValueError):pass
            time.sleep(1)
        return False


class Updater:
    def __init__(self,root=Path('/'),runtime=None):
        self.root=Path(root);self.state=self.root/'var/lib/dataark-software-updates';self.trust=self.root/'etc/dataark/software-update-keys'
        self.runtime=runtime or Runtime()
        if self.state.is_symlink():raise ValueError('Updater state must not be a symlink')
        self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
    def destination(self,name):
        if not allowed(name):raise ValueError('Unsupported software path')
        group,relative=name.split('/',1)
        base=self.root/('opt/dataark' if group=='source' else 'var/www/html')
        path=base/relative
        for parent in [path,*path.parents]:
            if parent.is_symlink():raise ValueError('Symlink in installation path')
            if parent==self.root:break
        if path.exists() and not path.is_file():raise ValueError('Software destination is not a regular file')
        return path
    def lock(self):
        stream=(self.state/'lock').open('a')
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:stream.close();raise ValueError('A software operation is already running') from None
        return stream
    def receipt(self):return json.loads((self.state/'installed.json').read_text())
    def build_files(self):
        paths=[self.root/'opt/dataark/app/static/assets/build-info.json',self.root/'var/www/html/assets/build-info.json']
        for path in paths:
            for parent in (path,*path.parents):
                if parent.is_symlink():raise ValueError('Symlink in build metadata path')
                if parent==self.root:break
        return paths
    def enroll(self,revision,profile):
        if not REV.fullmatch(revision) or not ID.fullmatch(profile):raise ValueError('Invalid enrollment identity')
        if (self.state/'installed.json').exists():raise ValueError('Already enrolled; refusing to replace the baseline')
        files={}
        for group,base in [('source',self.root/'opt/dataark'),('web',self.root/'var/www/html')]:
            for prefix in ('app','docs') if group=='source' else ('assets/js','assets/css','config','docs'):
                for path in (base/prefix).rglob('*'):
                    name=group+'/'+path.relative_to(base).as_posix()
                    if path.is_file() and allowed(name):files[name]=digest(self.destination(name))
        save(self.state/'installed.json',{'schema':1,'revision':revision,'sequence':0,'profile':profile,'files':files})
    def signature(self,stage):
        keys=sorted(self.trust.glob('*.pem'))[:16]
        for key in keys:
            if key.is_symlink() or key.stat().st_mode&0o022 or (os.geteuid()==0 and key.stat().st_uid!=0):continue
            result=subprocess.run(['/usr/bin/openssl','pkeyutl','-verify','-pubin','-inkey',str(key),'-rawin','-in',str(stage/'manifest.json'),'-sigfile',str(stage/'manifest.sig')],capture_output=True,timeout=5)
            if result.returncode==0:return
        raise ValueError('Package signature is not trusted')
    def validate(self,stage,baseline=True):
        self.signature(stage)
        raw=(stage/'manifest.json').read_bytes()
        if len(raw)>1024*1024:raise ValueError('Manifest is too large')
        m=json.loads(raw,object_pairs_hook=unique)
        required={'schema','release','sequence','source_revision','base_revision','profiles','requirements_sha256','configuration_schema','migrations','files','removals'}
        if set(m)!=required or m['schema']!=1 or m['configuration_schema']!=1 or m['migrations']!=[]:raise ValueError('Unsupported package or schema migration')
        if not isinstance(m['release'],str) or not ID.fullmatch(m['release']) or not isinstance(m['source_revision'],str) or not REV.fullmatch(m['source_revision']):raise ValueError('Invalid release identity')
        receipt=self.receipt()
        if m['base_revision']!=receipt['revision'] or type(m['sequence']) is not int or m['sequence']<=receipt['sequence']:raise ValueError('Wrong base revision or downgrade')
        if not isinstance(m['profiles'],list) or receipt['profile'] not in m['profiles']:raise ValueError('Package does not support this platform profile')
        if m['requirements_sha256']!=digest(self.root/'opt/dataark/requirements.txt'):raise ValueError('Dependency changes require a separately tested updater')
        if not isinstance(m['files'],dict) or not m['files'] or len(m['files'])>10000 or not isinstance(m['removals'],list):raise ValueError('Invalid file inventory')
        if len(set(m['removals']))!=len(m['removals']) or set(m['files'])&set(m['removals']):raise ValueError('Duplicate or conflicting file operations')
        for name,item in m['files'].items():
            destination=self.destination(name)
            if not isinstance(item,dict) or set(item)!={'sha256','bytes'} or not isinstance(item['sha256'],str) or not SHA.fullmatch(item['sha256']) or type(item['bytes']) is not int or not 0<=item['bytes']<=MAX_BYTES:raise ValueError('Invalid file digest')
            path=stage/'payload'/name
            if not path.is_file() or path.is_symlink() or path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:raise ValueError('Package content verification failed')
            if destination.exists() and name not in receipt['files']:raise ValueError('Refusing to replace an untracked local file')
        for name in m['removals']:
            self.destination(name)
            if name not in receipt['files']:raise ValueError('Removal is outside the enrolled baseline')
        if baseline:
            for name,expected in receipt['files'].items():
                path=self.destination(name)
                if not path.is_file() or digest(path)!=expected:raise ValueError('Local software edits require review before updating: '+name)
        return m
    def stage(self,archive):
        with self.lock():
            if archive.is_symlink() or not archive.is_file() or archive.stat().st_size>MAX_BYTES:raise ValueError('Invalid package file')
            identifier=uuid.uuid4().hex
            folder=self.state/'staged'/identifier;folder.mkdir(parents=True,mode=0o700)
            try:
                # Snapshot the submitted bytes into root-owned storage first.
                if shutil.disk_usage(self.state).free<MAX_BYTES*4+64*1024*1024:raise ValueError('Insufficient staging reserve')
                with archive.open('rb') as stream,(folder/'package.tar.gz').open('wb') as out:
                    remaining=MAX_BYTES
                    while chunk:=stream.read(min(1024*1024,remaining+1)):
                        remaining-=len(chunk)
                        if remaining<0:raise ValueError('Package grew beyond the size limit')
                        out.write(chunk)
                os.chmod(folder/'package.tar.gz',0o600)
                expanded=0
                with gzip.open(folder/'package.tar.gz','rb') as stream,(folder/'package.tar').open('wb') as out:
                    while chunk:=stream.read(1024*1024):
                        expanded+=len(chunk)
                        if expanded>MAX_BYTES+16*1024*1024:raise ValueError('Expanded archive exceeds the limit')
                        out.write(chunk)
                total=0;seen=set()
                with tarfile.open(folder/'package.tar','r:') as tar:
                    for item in tar:
                        name=item.name
                        if not item.isfile() or name in seen or len(seen)>=10002:raise ValueError('Archive contains duplicate or non-regular entries')
                        seen.add(name)
                        if name not in ('manifest.json','manifest.sig') and (not name.startswith('payload/') or not allowed(name[8:])):raise ValueError('Archive contains an unsupported path')
                        total+=item.size
                        if item.size<0 or total>MAX_BYTES:raise ValueError('Expanded package exceeds the limit')
                        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
                        with tar.extractfile(item) as stream,target.open('wb') as out:shutil.copyfileobj(stream,out)
                if not {'manifest.json','manifest.sig'}<=seen:raise ValueError('Signed manifest missing')
                manifest=self.validate(folder)
                expected={'manifest.json','manifest.sig'}|{'payload/'+name for name in manifest['files']}
                if seen!=expected:raise ValueError('Unlisted package content')
                sizes=[self.destination(name).stat().st_size for name in list(manifest['files'])+manifest['removals'] if self.destination(name).exists()]
                needed=total+sum(sizes)+max(sizes,default=0)+64*1024*1024
                if shutil.disk_usage(self.state).free<needed:raise ValueError('Insufficient space for staging and rollback')
                save(folder/'verified.json',{'id':identifier,'release':manifest['release'],'revision':manifest['source_revision']})
                (folder/'package.tar').unlink();(folder/'package.tar.gz').unlink()
                return {'id':identifier,'release':manifest['release'],'files':len(manifest['files']),'removals':len(manifest['removals'])}
            except BaseException:
                shutil.rmtree(folder);raise
    def stage_path(self,identifier):
        if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier):raise ValueError('Invalid staged package ID')
        folder=self.state/'staged'/identifier
        if folder.is_symlink() or not folder.is_dir():raise ValueError('Staged package not found')
        return folder
    def journal(self):
        try:return json.loads((self.state/'transaction.json').read_text())
        except FileNotFoundError:return {'state':'idle'}
    def restore(self,journal,boot=False):
        if not boot:self.runtime.stop()
        backup=self.state/'transactions'/journal['id']
        for name,metadata in journal['originals'].items():
            target=self.destination(name)
            if metadata is None:target.unlink(missing_ok=True)
            else:
                atomic(target,(backup/name).read_bytes(),metadata['mode']);os.chown(target,metadata['uid'],metadata['gid'])
        for index,metadata in enumerate(journal.get('build_files',[])):
            target=self.build_files()[index]
            if metadata is None:target.unlink(missing_ok=True)
            else:
                atomic(target,(backup/('build-'+str(index))).read_bytes(),metadata['mode']);os.chown(target,metadata['uid'],metadata['gid'])
        atomic(self.state/'installed.json',(backup/'installed.json').read_bytes())
        if not boot:
            self.runtime.start()
            if not self.runtime.healthy():raise ValueError('Rollback health check failed; local recovery required')
        journal['state']='rollback_pending_health' if boot else 'rolled_back';save(self.state/'transaction.json',journal)
    def recover(self,boot=False):
        with self.lock():
            journal=self.journal()
            if journal['state'] in ('applying','checking','rolling_back'):
                self.restore(journal,boot)
            elif journal['state']=='preparing':
                if not boot:self.runtime.start()
                journal['state']='interrupted_before_apply';save(self.state/'transaction.json',journal)
            return self.journal()
    def verify_recovery(self):
        with self.lock():
            journal=self.journal()
            if journal['state']=='rollback_pending_health':
                if not self.runtime.healthy():raise ValueError('Recovered software failed health checks')
                journal['state']='rolled_back';save(self.state/'transaction.json',journal)
            return journal
    def apply(self,identifier,checkpoint=None):
        with self.lock():
            if self.journal()['state'] in ('preparing','applying','checking','rolling_back'):raise ValueError('Recover the interrupted update first')
            folder=self.stage_path(identifier);m=self.validate(folder);self.runtime.preflight()
            sizes=[self.destination(name).stat().st_size for name in list(m['files'])+m['removals'] if self.destination(name).exists()]
            required=sum(v['bytes'] for v in m['files'].values())+sum(sizes)+max(sizes,default=0)+64*1024*1024
            if shutil.disk_usage(self.state).free<required:raise ValueError('Insufficient rollback reserve')
            for group in ('opt/dataark','var/www/html'):
                base=self.root/group
                if base.exists() and shutil.disk_usage(base).free<required:raise ValueError('Insufficient destination/rollback reserve')
            receipt=self.receipt();backup=self.state/'transactions'/identifier
            if backup.exists():raise ValueError('Transaction ID has already been used')
            backup.mkdir(parents=True,mode=0o700)
            journal={'id':identifier,'state':'preparing','release':m['release'],'originals':{}}
            save(self.state/'transaction.json',journal)
            try:
                self.runtime.stop()
                # Detect edits after staging and before quiescence.
                self.validate(folder);self.runtime.preflight()
                atomic(backup/'installed.json',(self.state/'installed.json').read_bytes())
                originals={}
                for name in list(m['files'])+m['removals']:
                    target=self.destination(name)
                    if target.exists():
                        stat=target.stat();originals[name]={'mode':stat.st_mode&0o777,'uid':stat.st_uid,'gid':stat.st_gid}
                        atomic(backup/name,target.read_bytes())
                    else:originals[name]=None
                build_files=[]
                for index,target in enumerate(self.build_files()):
                    if target.is_symlink():raise ValueError('Build metadata must not be a symlink')
                    if target.exists():
                        stat=target.stat();build_files.append({'mode':stat.st_mode&0o777,'uid':stat.st_uid,'gid':stat.st_gid});atomic(backup/('build-'+str(index)),target.read_bytes())
                    else:build_files.append(None)
                journal.update(state='applying',originals=originals,build_files=build_files);save(self.state/'transaction.json',journal)
                for name in m['files']:
                    old=originals[name]
                    target=self.destination(name);atomic(target,(folder/'payload'/name).read_bytes(),old['mode'] if old else 0o644)
                    if old:os.chown(target,old['uid'],old['gid'])
                    elif os.geteuid()==0:
                        stat=(self.root/'opt/dataark').stat();os.chown(target,stat.st_uid,stat.st_gid)
                    if checkpoint:checkpoint(name)
                for name in m['removals']:self.destination(name).unlink()
                journal['state']='checking';save(self.state/'transaction.json',journal)
                self.runtime.start()
                if not self.runtime.healthy():raise ValueError('Updated software failed health checks')
                receipt.update(revision=m['source_revision'],sequence=m['sequence'],release=m['release'],installed_at=time.time())
                for name,item in m['files'].items():receipt['files'][name]=item['sha256']
                for name in m['removals']:receipt['files'].pop(name)
                build={'schema':1,'revision':m['source_revision'],'branch':'release: '+m['release'],
                    'source_date':None,'source_fingerprint':None,'published_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'software_package_manifest_sha256':digest(folder/'manifest.json')}
                for index,target in enumerate(self.build_files()):
                    save(target,build);target.chmod(0o644)
                    old=build_files[index]
                    if old:os.chown(target,old['uid'],old['gid'])
                save(self.state/'installed.json',receipt)
                journal['state']='completed';save(self.state/'transaction.json',journal)
            except Exception as error:
                if journal['state']=='preparing':
                    self.runtime.start();journal.update(state='refused',error=str(error)[:300]);save(self.state/'transaction.json',journal)
                    return journal
                journal.update(state='rolling_back',error=str(error)[:300]);save(self.state/'transaction.json',journal)
                self.restore(journal)
            return self.journal()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    enroll=commands.add_parser('enroll');enroll.add_argument('--revision',required=True);enroll.add_argument('--profile',required=True)
    stage=commands.add_parser('stage');stage.add_argument('archive',type=Path)
    apply=commands.add_parser('apply');apply.add_argument('identifier')
    commands.add_parser('recover');commands.add_parser('status')
    args=parser.parse_args()
    if os.geteuid()!=0:parser.exit(1,'Root is required.\n')
    os.umask(0o077);updater=Updater()
    if args.command=='enroll':result=updater.enroll(args.revision,args.profile)
    elif args.command=='stage':result=updater.stage(args.archive)
    elif args.command=='apply':result=updater.apply(args.identifier)
    elif args.command=='recover':result=updater.recover()
    else:result=updater.journal()
    print(json.dumps(result))

if __name__=='__main__':main()
