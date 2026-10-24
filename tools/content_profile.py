#!/usr/bin/env python3
"""Export a readable content recipe, preview restoration, or restore explicitly.
Never removes content. Appliance/private configuration is a separate backup.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile,time,ssl
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
import yaml
REPO=Path(__file__).resolve().parents[1]
COLLECTIONS={
 'forms':('tools/install_forms.py',['--register'],'deploy/reference/forms-catalogue.json'),
 'family':('tools/install_family_resources.py',['--register'],'deploy/reference/family-catalogue.json'),
 'resilience':('tools/install_resilience.py',['--register'],'deploy/reference/resilience-catalogue.json'),
 'callsigns':('tools/install_callsigns.py',[],'deploy/reference/callsign-sources.json'),
 'radio-study':('tools/install_radio_study.py',[],'deploy/reference/radio-pools.json')}
REFERENCE_FILES=['family-catalogue.json','forms-catalogue.json','resilience-catalogue.json','resilience-settings.json','us-code-release.json','callsign-sources.json','radio-pools.json','osm-massachusetts.json','vehicle-manuals.json','honda-intermediate.pem','holiday-themes.json']
PUBLIC_KEYS=['system','geography','maps','categories','scenarios','repositories','assets','resource_sections']
def read(path):return yaml.safe_load(Path(path).read_text())
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);p=path.with_suffix(path.suffix+'.part');p.write_text(data);p.chmod(0o644);p.replace(path)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def inside(root,relative):
 p=PurePosixPath(relative)
 if p.is_absolute() or not p.parts or any(x in ('..','') for x in p.parts) or '\\' in relative:raise ValueError('Unsafe relative content path: '+relative)
 target=root.joinpath(*p.parts)
 if not target.resolve().is_relative_to(root.resolve()):raise ValueError('Content path escapes root')
 return target
def export(folder):
 manifest=read(REPO/'dataark.yaml');root=Path(manifest['system']['base_mount'])
 if not root.is_mount():raise ValueError('Content SSD is not mounted; existing selections were not changed.')
 if not any(inside(root,a['relative_path']).is_file() for a in manifest['assets']):raise ValueError('The content drive is empty. Keep the saved profile and use restore; do not replace selections with an empty inventory.')
 folder.mkdir(parents=True,exist_ok=True)
 public={k:manifest[k] for k in PUBLIC_KEYS if k in manifest};write(folder/'public-manifest.yaml',yaml.safe_dump(public,sort_keys=False,allow_unicode=True))
 files=[];coverage=[];archives=[];installed=[]
 for a in manifest['assets']:
  p=inside(root,a['relative_path']);present=p.is_file()
  if present:installed.append(a['id'])
  lock={'id':a['id'],'title':a.get('title',a['id']),'path':a['relative_path'],'selected':present,'bytes':p.stat().st_size if present else None,'sha256':a.get('expected_hash'),'source':a.get('download_url') or a.get('online_url'),'repository':a.get('repository_id')}
  coverage.append(lock)
  if a['relative_path'].endswith('.zim'):
   archives.append({'id':a['id'],'title':lock['title'],'enabled':present,'path':a['relative_path'],'url':a.get('download_url'),'bytes':lock['bytes'],'sha256':lock['sha256']})
  elif a.get('repository_id') in ('preparedness','vehicle-manuals') and present and a.get('download_url'):
   files.append({'id':a['id'],'path':a['relative_path'],'url':a['download_url'],'bytes':lock['bytes'],'sha256':lock['sha256']})
 state_path=root/'maps/status.json';state=json.loads(state_path.read_text()) if state_path.is_file() else {'files':{},'items':[]}
 mapfiles=[]
 for item in state.get('items',[]):
  meta=state.get('files',{}).get(item['id'],{});p=inside(root,'maps/'+item['path'])
  if p.is_file():mapfiles.append({'id':item['id'],'path':'maps/'+item['path'],'url':item['url'],'bytes':p.stat().st_size,'sha256':meta.get('sha256')})
 snapshots=[]
 for relative in ['maps/status.json','preparedness/sources.json','vehicles/sources.json','forms/sources.json','family-resources/sources.json','resilience/sources.json','civic-reference/sources.json','civic-reference/us-code-source.json','civic-reference/callsigns-source.json','radio-study/source.json']:
  p=inside(root,relative)
  if p.is_file():
   name='snapshots/'+relative;write(folder/name,p.read_text());snapshots.append(name)
 owned={a['relative_path'] for a in manifest['assets']}
 # Report large unregistered root archives, rather than silently treating stale copies as selected.
 unmanaged=[{'path':p.name,'bytes':p.stat().st_size,'note':'Not registered; preserve separately or add an explicit source recipe.'} for p in root.glob('*.zim') if p.name not in owned]
 recipe={'schema':1,'name':'Data Ark content selection','exported_at':datetime.now(timezone.utc).isoformat(),'source_repository':'https://github.com/DavJenkins/pharos','source_commit':subprocess.check_output(['git','-c','safe.directory='+str(REPO),'-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'content_root':str(root),'manifest':'public-manifest.yaml','reserve_gib':10,'download_rate_kib':0,'notes':['This file and referenced catalogues describe public content, not passwords, networking or private backups.','enabled=false preserves an uninstalled choice without downloading it.','Pinned archives require the recorded hash. Rolling publisher datasets and regenerated HTML may differ from the export.','No content is deleted by restoration. Source availability and network access are required unless files are supplied separately.'],'archives':archives,'direct_files':files,'map_files':mapfiles,'recipes':[{'id':'portable-reader','enabled':True,'url':next(a['download_url'] for a in manifest['assets'] if a['id']=='kiwix-windows-reader'),'target':'kiwix-viewer','files':[{'path':str(p.relative_to(root/'kiwix-viewer')),'bytes':p.stat().st_size} for p in sorted((root/'kiwix-viewer').rglob('*')) if p.is_file()],'note':'Keep the entire extracted Windows reader folder.'},{'id':'osm','enabled':True,'configuration':'deploy/reference/osm-massachusetts.json'},{'id':'forms','enabled':True,'catalogue':COLLECTIONS['forms'][2]},{'id':'family','enabled':True,'catalogue':COLLECTIONS['family'][2],'requires':['forms']},{'id':'resilience','enabled':True,'catalogue':COLLECTIONS['resilience'][2],'settings':'deploy/reference/resilience-settings.json','us_code_release':'deploy/reference/us-code-release.json'},{'id':'callsigns','enabled':True,'configuration':COLLECTIONS['callsigns'][2],'note':'FCC complete ZIP is a rolling source. Preserved source ZIP restores the old snapshot; otherwise a new snapshot is imported.'},{'id':'radio-study','enabled':True,'configuration':COLLECTIONS['radio-study'][2]},{'id':'indexes','enabled':True}],'snapshots':snapshots,'unmanaged_archives':unmanaged}
 write(folder/'content.yaml','# Public content recipe. Edit enabled flags and source catalogues; keep this folder with the source repository.\n'+yaml.safe_dump(recipe,sort_keys=False,allow_unicode=True));write(folder/'content-lock.json',json.dumps({'assets':coverage,'unmanaged_archives':unmanaged},indent=2)+'\n')
 if folder.resolve()==(REPO/'config/content').resolve():mirror(recipe,folder,root/'DATA-ARK-CONFIG')
 print('Exported',len(coverage),'registered asset records,',len(mapfiles),'installed map files; excluded private bugout/system-volume data.')
 if unmanaged:print('Unregistered archives need a separate decision:',', '.join(x['path'] for x in unmanaged))
 return recipe
def portable_files(c,folder):
 for name in ['content.yaml','content-lock.json',c['manifest']]+c.get('snapshots',[]):
  path=inside(folder,name)
  if path.is_file():yield path,'config/content/'+name
 for name in REFERENCE_FILES:
  path=REPO/'deploy/reference'/name
  if path.is_file():yield path,'deploy/reference/'+name

def mirror(c,folder,target):
 for path,name in portable_files(c,folder):
  out=inside(target,name);out.parent.mkdir(parents=True,exist_ok=True);part=out.with_suffix(out.suffix+'.part');shutil.copyfile(path,part);part.replace(out)
 write(target/'README.txt','Data Ark content configuration mirror\nAuthoritative copy: /opt/dataark/config/content on the Pi system drive.\nThis public mirror travels with the content drive. YAML/JSON files describe selections and source editions, not passwords or library payloads.\nKeep with the source repository: https://github.com/DavJenkins/pharos\nGuide: http://dataark/docs/20-Administration/ContentRestoration.html\nUse the system-drive profile to rebuild a replacement content drive. Do not export an empty inventory over it.\n')
 write(target/'index.html','<!doctype html><html><meta charset="utf-8"><title>Data Ark content configuration</title><h1>Data Ark content configuration</h1><p>Portable public mirror. The authoritative copy is /opt/dataark/config/content on the Pi system drive.</p><ul><li><a href="config/content/content.yaml">Content choices and restore recipes (YAML)</a></li><li><a href="config/content/public-manifest.yaml">Public library manifest (YAML)</a></li><li><a href="config/content/content-lock.json">Observed versions and hashes (JSON)</a></li></ul><a href="/docs/20-Administration/ContentRestoration.html">Restore and shipping guide</a></html>')
 print('Mirrored public configuration to',target)

def validate(c):
 if c.get('schema')!=1:raise ValueError('Unsupported content profile schema')
 ids=set()
 for item in c.get('archives',[])+c.get('direct_files',[])+c.get('map_files',[]):
  inside(Path('/tmp/profile-validation'),item['path'])
  u=urlsplit(item.get('url') or '')
  if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Expected public HTTPS source for '+item['id'])
  if item['id'] in ids:raise ValueError('Duplicate content id');
  ids.add(item['id'])
  if item.get('sha256') and (len(item['sha256'])!=64 or any(x not in '0123456789abcdef' for x in item['sha256'])):raise ValueError('Bad checksum')
 for r in c.get('recipes',[]):
  if r['id'] not in set(COLLECTIONS)|{'portable-reader','osm','indexes'}:raise ValueError('Unknown recipe '+r['id'])
 if type(c.get('reserve_gib')) not in (int,float) or c['reserve_gib']<1:raise ValueError('Reserve must be at least 1 GiB')
 if type(c.get('download_rate_kib',0)) is not int or c.get('download_rate_kib',0)<0:raise ValueError('Bad download rate')
def selected(c,only):
 only=list(only)
 known={'archives','direct_files','map_files'}|{i['id'] for key in ['archives','direct_files','map_files','recipes'] for i in c.get(key,[])}
 if set(only)-known:raise ValueError('Unknown selection: '+', '.join(sorted(set(only)-known)))
 for i in c.get('recipes',[]):
  if i['id'] in only:
   for dependency in i.get('requires',[]):
    if dependency not in only:only.append(dependency)
 jobs=[]
 for group in ['archives','direct_files','map_files']:
  for i in c.get(group,[]):
   if i.get('enabled',True) and (not only or group in only or i['id'] in only):jobs.append((group,i))
 for i in c.get('recipes',[]):
  if i.get('enabled',True) and (not only or i['id'] in only):jobs.append(('recipe',i))
 return jobs
def download(item,root,c,verify_existing=False):
 target=inside(root,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
 if target.is_file() and (not item.get('bytes') or target.stat().st_size==item['bytes']):
  if not verify_existing or not item.get('sha256') or digest(target)==item['sha256']:return 'present (size checked'+('; checksum checked' if verify_existing and item.get('sha256') else '')+')'
 size=item.get('bytes') or 2*1024**3
 if shutil.disk_usage(root).free-size<c['reserve_gib']*1024**3:raise RuntimeError('Insufficient free space above reserve')
 part=target.with_suffix(target.suffix+'.restore-part');args=['curl','--fail','--location','--proto','=https','--retry','2','--connect-timeout','30','--max-filesize',str(size),'--continue-at','-','--output',str(part)]
 if c.get('download_rate_kib'):args+=['--limit-rate',str(c['download_rate_kib'])+'K']
 # Honda omits an intermediate certificate. Supply its CA chain only for
 # this host, still validating the hostname and the system's trusted roots.
 with tempfile.TemporaryDirectory(prefix='dataark-download-ca-') as temporary:
  if urlsplit(item['url']).hostname=='techinfo.honda.com':
   roots=Path(ssl.get_default_verify_paths().cafile);bundle=Path(temporary)/'ca.pem'
   bundle.write_bytes(roots.read_bytes()+b'\n'+(REPO/'deploy/reference/honda-intermediate.pem').read_bytes())
   args+=['--cacert',str(bundle)]
  subprocess.run(args+[item['url']],check=True)
 if item.get('bytes') and part.stat().st_size!=item['bytes']:raise ValueError('Downloaded size mismatch; staged file retained')
 if item.get('sha256') and digest(part)!=item['sha256']:raise ValueError('Downloaded checksum mismatch; original file retained')
 if target.suffix=='.zim':
  with part.open('rb') as f:
   if f.read(4)!=b'ZIM\x04':raise ValueError('Not a ZIM archive')
 part.chmod(0o644);part.replace(target);return 'restored'
def recipe(item,c,root,folder):
 name=item['id']
 if name in COLLECTIONS:
  repositories={'forms':['forms-templates'],'family':['family-resources','food-preservation','sanitation','drinking-water'],'resilience':['resilience','civic-reference'],'callsigns':['civic-reference'],'radio-study':['radio-study']}
  manifest=read(REPO/'dataark.yaml');assets=[a for a in manifest.get('assets',[]) if a.get('repository_id') in repositories[name]]
  if name=='resilience':assets=[a for a in assets if not a['id'].startswith('callbook-')]
  if name=='callsigns':assets=[a for a in assets if a['id'].startswith('callbook-')]
  indexes={'forms':['forms/index.html','forms/sources.json','forms/cc-by-4.0.txt'],'family':['family-resources/index.html','family-resources/sources.json'],'resilience':['resilience/index.html','civic-reference/index.html'],'callsigns':['civic-reference/callsigns-source.json'],'radio-study':['radio-study/source.json']}
  complete=bool(assets) and all(inside(root,a['relative_path']).is_file() for a in assets) and all(inside(root,p).is_file() for p in indexes[name])
  if complete and name=='radio-study':
   metadata=json.loads((root/'radio-study/source.json').read_text());complete=all(inside(root/'radio-study',f['path']).is_file() for f in metadata['files'])
  if complete:print('Existing complete collection reused:',name,flush=True);return

  script,args,_=COLLECTIONS[name]
  if name=='resilience':
   meta=REPO/'deploy/reference/us-code-release.json';m=json.loads(meta.read_text());target=root/'civic-reference/us-code-source.zip'
   if not target.exists():download({'id':'usc-source','path':'civic-reference/us-code-source.zip','url':m['url'],'sha256':m['sha256']},root,c);write(root/'civic-reference/us-code-source.json',json.dumps(m,indent=2)+'\n')
  subprocess.run(['/usr/bin/python3',str(REPO/script)]+args,check=True);return
 if name=='portable-reader':
  target=inside(root,item['target'])
  expected=item.get('files',[])
  if expected and all(inside(target,f['path']).is_file() and inside(target,f['path']).stat().st_size==f['bytes'] for f in expected):return
  download({'id':name,'path':'.restore-cache/kiwix-windows.zip','url':item['url']},root,c)
  import zipfile
  with zipfile.ZipFile(root/'.restore-cache/kiwix-windows.zip') as z:
   if sum(x.file_size for x in z.infolist())>2*1024**3:raise ValueError('Reader ZIP too large')
   candidates=[x.filename for x in z.infolist() if x.filename.endswith('kiwix-desktop.exe')]
   if len(candidates)!=1:raise ValueError('Reader executable not uniquely found')
   prefix=str(PurePosixPath(candidates[0]).parent);prefix='' if prefix=='.' else prefix+'/'
   for member in z.infolist():
    if member.is_dir() or not member.filename.startswith(prefix):continue
    if (member.external_attr>>16)&0o170000==0o120000:raise ValueError('ZIP symlink rejected')
    out=inside(target,member.filename[len(prefix):]);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix(out.suffix+'.restore-part')
    with z.open(member) as src,tmp.open('wb') as dst:shutil.copyfileobj(src,dst)
    tmp.replace(out)
  return
 if name=='osm':
  m=json.loads((REPO/item['configuration']).read_text());target=root/'maps/osm/massachusetts.pmtiles'
  if target.is_file():return
  if not shutil.which('pmtiles'):raise RuntimeError('Install the documented pmtiles CLI first')
  target.parent.mkdir(parents=True,exist_ok=True);part=target.with_suffix('.restore-part')
  subprocess.run(['pmtiles','extract',m['source'],str(part),'--bbox='+','.join(map(str,m['bbox'])),'--maxzoom='+str(m['maxzoom'])],check=True)
  if m.get('sha256') and digest(part)!=m['sha256']:raise ValueError('Map checksum mismatch; review extractor/source edition before accepting')
  part.replace(target);return
 if name=='indexes':
  sys.path.insert(0,str(REPO))
  statefile=folder/'snapshots/maps/status.json'
  if statefile.is_file():
   from tools.map_worker import publish as publish_maps
   state=json.loads(statefile.read_text());publish_maps(root/'maps',state['items'],state,'Configured Massachusetts reference maps');write(root/'maps/status.json',json.dumps(state,indent=2)+'\n')
  prep=folder/'snapshots/preparedness/sources.json'
  if prep.is_file():
   import html
   rows=json.loads(prep.read_text());links=''.join('<li><a href="'+html.escape(r['filename'],quote=True)+'">'+html.escape(r['title'])+'</a> — '+html.escape(r.get('edition',''))+'</li>' for r in rows if r.get('status')=='installed' and (root/'preparedness'/r['filename']).is_file());write(root/'preparedness/index.html','<!doctype html><html><meta charset="utf-8"><title>Preparedness</title><a href="/">Library</a><h1>Emergency preparedness and CERT</h1><ul>'+links+'</ul><a href="sources.json">Source dates and coverage</a></html>');write(root/'preparedness/sources.json',prep.read_text())
  from tools.publish_content import publish
  publish(root)
  subprocess.run(['bash',str(REPO/'deploy/deploy-web.sh')],check=True)
  if any(x.get('enabled') for x in c.get('archives',[])) and shutil.which('docker'):
   subprocess.run(['docker','restart','kiwix-serve'],check=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 e=sub.add_parser('export');e.add_argument('--output',type=Path,default=REPO/'config/content')
 for action in ['plan','restore','mirror']:
  a=sub.add_parser(action);a.add_argument('--profile',type=Path,default=REPO/'config/content/content.yaml');a.add_argument('--only',action='append',default=[])
  if action=='restore':a.add_argument('--apply',action='store_true');a.add_argument('--verify-existing',action='store_true')
 b=sub.add_parser('bundle');b.add_argument('--profile',type=Path,default=REPO/'config/content/content.yaml');b.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.action=='export':export(a.output);return
 c=read(a.profile);validate(c);folder=a.profile.parent
 if a.action=='bundle':
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with tarfile.open(a.output,'w:gz') as t:

   for path,name in portable_files(c,folder):t.add(path,arcname=name,recursive=False)
  print('Content configuration bundle:',a.output,'— keep with the matching source repository. No library payloads or private settings included.');return
 if a.action=='mirror':
  root=Path(c['content_root'])
  if not root.is_mount():raise SystemExit('Content SSD must be mounted')
  mirror(c,folder,root/'DATA-ARK-CONFIG');return
 jobs=selected(c,a.only);root=Path(c['content_root']);print('Content root:',root,'\nNo removal operations are defined.')
 for kind,i in jobs:print(kind+': '+i['id']+(' -> '+i.get('path','') if kind!='recipe' else ''))
 if a.action=='plan' or not a.apply:print('Preview only. Use restore --apply to download/regenerate.');return
 if os.geteuid()!=0:raise SystemExit('Run the explicit restore with sudo.')
 if root!=Path('/mnt/storage') or not root.is_mount():raise SystemExit('Restore currently requires the configured content SSD mounted at /mnt/storage.')
 import fcntl
 restore_lock=Path('/var/lib/dataark/content-restore.lock').open('a')
 fcntl.flock(restore_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as shared:
  fcntl.flock(shared,fcntl.LOCK_EX|fcntl.LOCK_NB)
  # Apply public selections, retaining existing system and private appliance settings.
  public=read(inside(folder,c['manifest']));live=read(REPO/'dataark.yaml') if (REPO/'dataark.yaml').exists() else public
  for key in PUBLIC_KEYS:
   if key!='system' and key in public:live[key]=public[key]
  write(REPO/'dataark.yaml',yaml.safe_dump(live,sort_keys=False,allow_unicode=True))
 failures=[]
 for kind,i in jobs:
  try:
   print('Running',i['id'],flush=True)
   if kind=='recipe':recipe(i,c,root,folder)
   else:
    lockfile=Path('/var/lib/dataark/maps/worker.lock' if kind=='map_files' else '/var/lib/dataark/updates/worker.lock');lockfile.parent.mkdir(parents=True,exist_ok=True)
    with lockfile.open('a') as shared:
     fcntl.flock(shared,fcntl.LOCK_EX|fcntl.LOCK_NB);print(download(i,root,c,a.verify_existing),flush=True)
  except Exception as error:failures.append({'id':i['id'],'error':str(error)});print('FAILED',i['id'],str(error),flush=True)
 report={'completed_at':datetime.now(timezone.utc).isoformat(),'jobs':len(jobs),'failures':failures};write(folder/'last-restore.json',json.dumps(report,indent=2)+'\n')
 if failures:raise SystemExit('Some items need attention; see last-restore.json. Verified originals were retained.')
 print('Restore finished. Check local readers and source coverage before declaring the appliance ready.')
if __name__=='__main__':main()
