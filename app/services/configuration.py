"""Caretaker editing of the public content manifest, preserving private settings."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
import yaml
from app.services.manifest import load_manifest, UniqueLoader, ManifestError, atomic_write
from app.services.dashboard_cards import compose
from app.services import configuration_project as project

ROOT=Path(__file__).resolve().parents[2]
STATE=Path('/var/lib/dataark/configuration')
KEYS=project.PUBLIC_KEYS

def stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def revision(raw):return hashlib.sha256(raw).hexdigest()
def dump(value):return yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
def public(data):return project.public(data)
def current():
    path=ROOT/'dataark.yaml';raw=path.read_bytes();return raw,load_manifest(path)
def write_json(path,value):
    atomic_write(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode());path.chmod(0o600)
    if os.geteuid()==0:
        import pwd
        account=pwd.getpwnam('admin');os.chown(path,account.pw_uid,account.pw_gid)

def status():
    try:
        value=json.loads((STATE/'status.json').read_text())
        if value.get('state') in ('queued','publishing') and value.get('updated_at'):
            elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(value['updated_at'])).total_seconds()
            if elapsed>30:
                import subprocess
                active=subprocess.run(['/usr/bin/systemctl','is-active','dataark-configuration-publish.service'],capture_output=True,text=True,timeout=3).stdout.strip()
                if active not in ('active','activating','reloading'):
                    value={**value,'state':'error','message':'Configuration publication was interrupted. Reload to inspect the current configuration or load a saved version.'}
                    write_json(STATE/'status.json',value)
        return value
    except (OSError,ValueError):return {'state':'idle','message':'No configuration publication in progress.'}

def read(file=None):
    raw,data=current();view=public(data);text=''
    saved=ROOT/'config/content/public-manifest.yaml'
    if file is None:
        text=dump(view)
        try:
            candidate=saved.read_text(encoding='utf-8')
            if yaml.load(candidate,Loader=UniqueLoader)==view:text=candidate
        except (OSError,ValueError,yaml.YAMLError):pass
    history=[]
    for path in (STATE/'history').glob('*.json'):
        try:
            item=json.loads(path.read_text());history.append({'id':path.stem,'saved_at':item['saved_at']})
        except (OSError,ValueError,KeyError):continue
    files=project.view_files(ROOT/'config/library',view)
    warning=''
    try:project.ensure_clean(ROOT/'config/library')
    except (ValueError,OSError,KeyError):warning='There are unpublished modular-file edits on disk. Compile and review them before saving other changes.'
    if file is not None:
        if file not in files:raise ValueError('Unknown configuration file.')
        text=files[file]
    return {'text':text,'file':file,'files':project.metadata(files),'read_only':bool(file and file.startswith('state/')),'project_warning':warning,'revision':revision(raw),'community_enabled':view['community']['enabled'],'history':sorted(history,key=lambda item:item['saved_at'],reverse=True)[:20],'status':status()}

def checked(text,live,file=None):
    if not isinstance(text,str) or len(text.encode('utf-8'))>4*1024*1024:raise ValueError('Configuration must be UTF-8 YAML, no larger than 4 MiB.')
    if file is not None:
        files=project.view_files(ROOT/'config/library',public(live))
        if file not in files or file.startswith('state/'):raise ValueError('Unknown or generated read-only configuration file.')
        files[file]=text
        try:value,_=project.assemble(files.__getitem__)
        except KeyError as error:raise ValueError('Referenced project file is missing: '+str(error)) from None
        except yaml.YAMLError as error:raise ValueError('Invalid project YAML: '+str(error)) from None
        text=dump(value)
    try:value=yaml.load(text,Loader=UniqueLoader)
    except yaml.YAMLError as error:raise ValueError('Invalid YAML: '+str(error)) from None
    if not isinstance(value,dict) or set(value)-set(KEYS):raise ValueError('Use only the public content configuration sections shown by Load configuration.')
    def bounded(item,depth=0,budget=[0]):
        budget[0]+=1
        if depth>30 or budget[0]>250000:raise ValueError('Configuration is too deeply nested or contains recursive aliases.')
        if isinstance(item,dict):
            for child in item.values():bounded(child,depth+1,budget)
        elif isinstance(item,list):
            for child in item:bounded(child,depth+1,budget)
    bounded(value,budget=[0])
    editable_system={'project_name','theme','artwork'}
    if not isinstance(value.get('system'),dict):raise ValueError('Keep the system section.')
    if {k:v for k,v in value['system'].items() if k not in editable_system}!={k:v for k,v in live['system'].items() if k not in editable_system}:
        raise ValueError('Storage paths, service addresses and schema version are read-only in this content editor.')
    merged=dict(live)
    for key in KEYS:
        if key in value:merged[key]=value[key]
        else:merged.pop(key,None)
    merged.setdefault('community',{'enabled':True})
    descriptor,name=tempfile.mkstemp(suffix='.yaml',dir=ROOT)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:stream.write(dump(merged))
        load_manifest(name)
    finally:Path(name).unlink(missing_ok=True)
    return merged

def preview(text,file=None):
    _,live=current();data=checked(text,live,file)
    rows={repo['id']:[] for repo in data.get('repositories',[])}
    for asset in data.get('assets',[]):rows[asset['repository_id']].append(asset)
    cards,_=compose(data,rows)
    return {'community_enabled':data['community']['enabled'], 'categories':len(data.get('categories',[])),
            'assets':len(data.get('assets',[])), 'cards':[{'title':card.get('title',card['id']),'category':card['category'],'enabled':card.get('enabled',True)} for card in cards]}

def queue(text,expected,file=None,project_token=None):
    import fcntl
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'editor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if status().get('state') in ('queued','publishing'):raise ValueError('A configuration publication is already in progress.')
        raw,live=current()
        if expected!=revision(raw):raise ValueError('Configuration changed since you loaded it. Download your edits, then reload before saving.')
        if project_token is None:project.ensure_clean(ROOT/'config/library')
        else:
            if project.fingerprint(ROOT/'config/library')!=project_token:raise ValueError('Modular files changed; compile and review again.')
            project.assert_base(ROOT/'config/library',public(live))
        data=checked(text,live,file)
        identifier=uuid.uuid4().hex
        job={'id':identifier,'text':dump(public(data)) if file is not None else text,'revision':expected}
        if file is not None:job['source_edit']={'file':file,'text':text}
        if project_token is not None:job['project_token']=project_token
        write_json(STATE/'pending.json',job)
        write_json(STATE/'status.json',{'id':identifier,'state':'queued','message':'Configuration is queued for publication.','updated_at':stamp()})
        from app.services.collection_changes import safe_record
        safe_record('configuration_queued', operation_id=identifier, action='configuration')
        return {'id':identifier,'state':'queued'}

def history(identifier):
    import re
    if not re.fullmatch(r'[0-9a-f]{32}',identifier):raise ValueError('Unknown saved version.')
    return json.loads((STATE/'history'/(identifier+'.json')).read_text())
