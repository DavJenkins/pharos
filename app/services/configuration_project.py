"""Readable public authoring files, lossless assembly, and guarded disk snapshots.

The combined manifest remains the compatibility boundary for existing writers.
Never derive desired selections from which files happen to exist on the SSD.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from contextlib import contextmanager
from collections import deque
import yaml

PUBLIC_KEYS=('system','geography','maps','categories','scenarios','repositories','assets','resource_sections','dashboard','personalization','community')
FORMAT='dataark-project-v1'


class Loader(getattr(yaml,'CSafeLoader',yaml.SafeLoader)):
    pass


def mapping(loader,node):
    result={}
    for key,value in node.value:
        key=loader.construct_object(key)
        if not isinstance(key,str) or key in result:raise ValueError('Project keys must be unique strings.')
        result[key]=loader.construct_object(value)
    return result


Loader.add_constructor('tag:yaml.org,2002:map',mapping)


def parse(text):
    if not isinstance(text,str) or len(text.encode())>4*1024**2:raise ValueError('Project file exceeds 4 MiB.')
    value=yaml.load(text,Loader=Loader)
    def bounded(node,depth=0,budget=None):
        budget[0]+=1
        if depth>30 or budget[0]>250000:raise ValueError('Project YAML is recursive or too large.')
        if isinstance(node,dict):
            for child in node.values():bounded(child,depth+1,budget)
        elif isinstance(node,list):
            for child in node:bounded(child,depth+1,budget)
    bounded(value,budget=[0])
    if not isinstance(value,dict):raise ValueError('Project files must contain mappings.')
    return value


def dump(value):return yaml.dump(value,Dumper=getattr(yaml,'CSafeDumper',yaml.SafeDumper),sort_keys=False,allow_unicode=True)


def atomic_write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,name=tempfile.mkstemp(dir=path.parent,prefix='.project-')
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'wb') as stream:stream.write(value);stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


def public(data):return {key:data[key] for key in PUBLIC_KEYS if key in data}|{'community':data.get('community',{'enabled':True})}


@contextmanager
def locked(root,exclusive=False):
    path=Path(root)/'.project.lock'
    if os.name!='posix' or (not exclusive and not path.exists()):yield;return
    import fcntl
    with path.open('a' if exclusive else 'r') as stream:
        if exclusive:
            path.chmod(0o644)
            if os.geteuid()==0:
                import pwd
                user=pwd.getpwnam('admin');os.chown(path,user.pw_uid,user.pw_gid)
        fcntl.flock(stream,fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield


def allowed(name):
    return isinstance(name,str) and bool(re.fullmatch(r'ark\.yaml|collections/[a-z0-9][a-z0-9_-]*\.yaml|catalogues/[a-z0-9][a-z0-9_-]*\.yaml|state/order\.yaml|state/versions/[a-z0-9][a-z0-9_-]*\.yaml',name))


def inside(root,name):
    if not allowed(name):raise ValueError('Unknown project path: '+str(name))
    root=Path(root).resolve();target=(root/PurePosixPath(name)).resolve()
    if not target.is_relative_to(root):raise ValueError('Project path escapes its directory.')
    return target


def split(data):
    """Keep exact definitions/order; only recorded checksums move to state."""
    data=public(data)
    settings={key:data[key] for key in PUBLIC_KEYS if key in data and key not in ('repositories','assets')}
    files={};references=[]
    groups={repo['id']:[] for repo in data.get('repositories',[])}
    for asset in data.get('assets',[]):
        if asset['repository_id'] not in groups:raise ValueError('Unknown asset repository.')
        groups[asset['repository_id']].append(asset)
    for repo in data.get('repositories',[]):
        identifier=repo['id'];name='collections/'+identifier+'.yaml'
        if not allowed(name):raise ValueError('Invalid collection identifier.')
        catalogue='catalogues/'+identifier+'.yaml';versions='state/versions/'+identifier+'.yaml'
        references.append(name)
        files[name]=dump({'repository':repo,'catalogue':catalogue,'versions':versions})
        files[catalogue]=dump({'assets':[{k:v for k,v in asset.items() if k!='expected_hash'} for asset in groups[identifier]]})
        files[versions]=dump({'hashes':{asset['id']:asset['expected_hash'] for asset in groups[identifier] if 'expected_hash' in asset}})
    files['state/order.yaml']=dump({'assets':[asset['id'] for asset in data.get('assets',[])]})
    files['ark.yaml']=dump({'format':FORMAT,'type_registry':'config/content-types.yaml','collections':references,'ordering':'state/order.yaml',**settings})
    return files


def assemble(reader):
    """reader(name) returns UTF-8 YAML; references are always project-relative."""
    cache={}
    total=0
    def read(name):
        nonlocal total
        if not allowed(name):raise ValueError('Unknown project path: '+str(name))
        if name not in cache:
            text=reader(name);total+=len(text.encode())
            if total>16*1024**2:raise ValueError('Combined project exceeds 16 MiB.')
            cache[name]=parse(text)
        return cache[name]
    main=read('ark.yaml')
    if main.get('format')!=FORMAT or main.get('type_registry')!='config/content-types.yaml':raise ValueError('Unsupported project format or type registry reference.')
    if set(main)-set(PUBLIC_KEYS)-{'format','collections','ordering','type_registry'} or 'repositories' in main or 'assets' in main:raise ValueError('Use collection files for repositories and catalogues for assets.')
    if not isinstance(main.get('collections'),list) or any(not isinstance(name,str) for name in main['collections']) or len(main['collections'])!=len(set(main['collections'])):raise ValueError('collections must list unique file names.')
    data={k:v for k,v in main.items() if k in PUBLIC_KEYS};repos=[];assets={}
    for name in main['collections']:
        if not isinstance(name,str) or not name.startswith('collections/'):raise ValueError('Invalid collection file.')
        collection=read(name)
        if set(collection)!={'repository','catalogue','versions'}:raise ValueError('Collections require repository, catalogue and versions.')
        repo=collection['repository']
        if not isinstance(repo,dict) or not isinstance(repo.get('id'),str) or name!='collections/'+repo['id']+'.yaml':raise ValueError('Collection file and repository ID must match.')
        repos.append(repo)
        if collection['catalogue']!='catalogues/'+repo['id']+'.yaml' or collection['versions']!='state/versions/'+repo['id']+'.yaml':raise ValueError('Collection catalogue/version paths must match its ID.')
        catalogue=read(collection['catalogue']);versions=read(collection['versions'])
        if set(catalogue)!={'assets'} or not isinstance(catalogue['assets'],list) or set(versions)!={'hashes'} or not isinstance(versions['hashes'],dict):raise ValueError('Invalid catalogue or versions snapshot.')
        for original in catalogue['assets']:
            if not isinstance(original,dict) or not isinstance(original.get('id'),str):raise ValueError('Catalogue records need asset IDs.')
            asset=dict(original)
            if asset.get('repository_id')!=repo['id'] or asset['id'] in assets:raise ValueError('Duplicate asset or mismatched repository.')
            if 'expected_hash' not in asset and asset['id'] in versions['hashes']:asset['expected_hash']=versions['hashes'][asset['id']]
            assets[asset['id']]=asset
    if main.get('ordering')!='state/order.yaml':raise ValueError('Use the generated state/order.yaml ordering snapshot.')
    order=read(main['ordering'])
    if set(order)!={'assets'} or not isinstance(order['assets'],list) or any(not isinstance(key,str) for key in order['assets']) or len(set(order['assets']))!=len(order['assets']):raise ValueError('Invalid ordering snapshot.')
    # Preserve legacy interleaving while honoring each catalogue's human-chosen order.
    queues={repo['id']:deque(key for key,asset in assets.items() if asset['repository_id']==repo['id']) for repo in repos}
    ordered=[]
    for key in order['assets']:
        if key in assets:
            queue=queues[assets[key]['repository_id']]
            if queue:ordered.append(queue.popleft())
    for repo in repos:ordered.extend(queues[repo['id']])
    data.update(repositories=repos,assets=[assets[key] for key in ordered])
    data.setdefault('community',{'enabled':True})
    return data,list(cache)


def load(entry):
    entry=Path(entry)
    if entry.name!='ark.yaml':raise ValueError('Project entry must be named ark.yaml.')
    root=entry.parent
    with locked(root):return assemble(lambda name:inside(root,name).read_text(encoding='utf-8'))[0]


def metadata(files):
    return [{'path':name,'read_only':name.startswith('state/'),'lines':text.count('\n'),'bytes':len(text.encode())} for name,text in sorted(files.items(),key=lambda item:(item[0]!='ark.yaml',item[0]))]


def disk_files(root):
    root=Path(root)
    if not (root/'ark.yaml').exists():return {}
    with locked(root):
        _,names=assemble(lambda name:inside(root,name).read_text(encoding='utf-8'))
        return {name:inside(root,name).read_text(encoding='utf-8') for name in names}


def fingerprint(root):
    digest=hashlib.sha256()
    for name,text in sorted(disk_files(root).items()):digest.update(name.encode()+b'\0'+text.encode()+b'\0')
    index=Path(root)/'.layout.json'
    if index.exists():digest.update(index.read_bytes())
    return digest.hexdigest()


def public_digest(data):return hashlib.sha256(yaml.dump(public(data),Dumper=getattr(yaml,'CSafeDumper',yaml.SafeDumper),sort_keys=True,allow_unicode=True).encode()).hexdigest()


def assert_base(root,active):
    try:base=json.loads((Path(root)/'.layout.json').read_text())['public_sha256']
    except (OSError,ValueError,KeyError):raise ValueError('Project needs a reviewed synchronization record before local publication.') from None
    if base!=public_digest(active):raise ValueError('The active manifest changed since this project was synchronized. Reconcile the modular draft with the active configuration before publishing.')


def view_files(root,data):
    """Use saved comments only when the on-disk project represents this active view."""
    try:
        existing=disk_files(root)
        if existing and public(assemble(existing.__getitem__)[0])==public(data):return existing
    except (ValueError,OSError,KeyError,yaml.YAMLError):pass
    return split(data)


def ensure_clean(root):
    """Do not overwrite a person's disk edits with an automatic projection."""
    root=Path(root);index=root/'.layout.json'
    if not (root/'ark.yaml').exists():return
    if not index.is_file():raise ValueError('Existing modular project has no synchronization record; preserve it and compile/review it before replacing it.')
    expected=json.loads(index.read_text())['files']
    for name,digest in expected.items():
        path=inside(root,name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Modular configuration has manual edits: '+name+'. Compile and review those edits before publishing another change.')


def write_files(root,files):
    """Roll back all touched files if any write fails; leave unrelated files alone."""
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    with locked(root,True):_write_files(root,files)


def _write_files(root,files):
    previous={name:inside(root,name).read_bytes() if inside(root,name).exists() else None for name in files}
    index=root/'.layout.json';old_index=index.read_bytes() if index.exists() else None
    def owner(path):
        path.chmod(0o755 if path.is_dir() else 0o644)
        if os.name=='posix' and os.geteuid()==0:
            import pwd
            user=pwd.getpwnam('admin');os.chown(path,user.pw_uid,user.pw_gid)
    try:
        owner(root)
        for name,text in files.items():
            target=inside(root,name);target.parent.mkdir(parents=True,exist_ok=True)
            for parent in target.parents:
                if parent==root:break
                owner(parent)
            atomic_write(target,text.encode());owner(target)
        assembled,_=assemble(files.__getitem__)
        atomic_write(index,json.dumps({'schema':1,'public_sha256':public_digest(assembled),'files':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()}},indent=2).encode());owner(index)
    except Exception:
        for name,value in previous.items():
            path=inside(root,name)
            if value is None:path.unlink(missing_ok=True)
            else:atomic_write(path,value);owner(path)
        if old_index is None:index.unlink(missing_ok=True)
        else:atomic_write(index,old_index);owner(index)
        raise


def write(root,data,overrides=None):
    ensure_clean(root);files=split(data)
    for name,text in disk_files(root).items():
        if name in files and parse(text)==parse(files[name]):files[name]=text
    for name,text in (overrides or {}).items():
        if name not in files or name.startswith('state/'):raise ValueError('Unknown or generated project file.')
        files[name]=text
    assembled,_=assemble(files.__getitem__)
    expected=public(data)
    if assembled!=expected:raise ValueError('Modular projection differs from the public configuration.')
    write_files(root,files)
    return files
