#!/usr/bin/env python3
"""Bounded public constitution acquisition for all configured U.S. jurisdictions.
Human-readable sources: deploy/reference/jurisdictions.json. Does not claim complete statutes.
"""
import argparse, concurrent.futures, hashlib, html, json, re, subprocess, sys, tempfile, urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
DEST=Path('/mnt/storage/civic-reference/jurisdictions')
class Links(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.href=None;self.words=[]
 def handle_starttag(self,t,a):
  if t=='a':self.href=dict(a).get('href');self.words=[]
 def handle_data(self,d):
  if self.href is not None:self.words.append(d)
 def handle_endtag(self,t):
  if t=='a' and self.href is not None:self.rows.append((' '.join(''.join(self.words).split()),self.href));self.href=None

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (DataArk public legal reference archive)'})
 with urllib.request.urlopen(req,timeout=20) as r:
  if urlsplit(r.url).scheme not in ('http','https'):raise ValueError('Unexpected redirect scheme')
  data=r.read(50*1024**2+1);resolved=r.url
 if len(data)>50*1024**2:raise ValueError('Exceeds 50 MiB document cap')
 return data,resolved

def validate_text(text,name):
 plain=' '.join(text.split()).lower()
 if len(plain)<12000:raise ValueError('Too little substantive text; index pages are not constitutions')
 if not any(x in plain for x in ['constitution','constituci','home rule']):raise ValueError('Not a constitutional/charter document')
 if name.lower() not in plain:raise ValueError('Jurisdiction identity not verified')
 if not any(x in plain for x in ['governor','gobernador','mayor']):raise ValueError('Executive provisions not verified')
 if not any(x in plain for x in ['legislat','legislat','asamblea','council']):raise ValueError('Legislative provisions not verified')
 if any(x in plain[:1200] for x in ['access denied','verify you are human','enable javascript and cookies']):raise ValueError('Publisher access page, not content')
 return plain

def university_body(source):
 match=re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',source,re.S)
 if not match:raise ValueError('Missing public constitutional data')
 values=json.loads(match[1])
 root=values[values[1]['data']]
 key=next(k for k in root if k.startswith('useConstitutionEntriesAll'))
 references=values[root[key]]
 pieces=[];count=0
 def value(entry,key):
  index=entry.get(key)
  return values[index] if isinstance(index,int) and index>=0 else None
 for index in references:
  entry=values[index]
  if not isinstance(entry,dict) or 'clause' not in entry:continue
  title=value(entry,'title') or value(entry,'catchline') or ''
  clause=value(entry,'clause')
  if title:pieces.append('<h2>'+html.escape(str(title))+'</h2>')
  if isinstance(clause,str) and clause.strip():
   pieces.append('<div class="constitutional-provision">'+''.join('<p>'+html.escape(line)+'</p>' for line in clause.splitlines() if line.strip())+'</div>');count+=1
 if count<10:raise ValueError('Too few substantive constitutional provisions')
 body=''.join(pieces)
 return body,html.unescape(re.sub('<[^>]+>',' ',body)),count,key.removeprefix('useConstitutionEntriesAll')

def acquire(row):
 from tools.install_resilience import body_copy,atomic
 record={**row,'checked_at':datetime.now(timezone.utc).isoformat(),'status':'unavailable','attempts':[],'statutes_status':'Not mirrored; source discovery only'}
 if row.get('framework_title48'):
  candidates=sorted((DEST.parent/'us-code').glob('*48*.htm*'))
  if candidates:
   record.update(status='framework-only',framework_url='../us-code/'+candidates[0].name,scope='Federal Title 48 territorial framework only; local constitution and code not archived')
  return record
 queue=[(u,0) for u in row.get('constitution_candidates',[])];seen=set()
 while queue and len(seen)<9:
  url,depth=queue.pop(0)
  if url in seen:continue
  seen.add(url)
  try:
   data,resolved=fetch(url)
   if data.startswith(b'%PDF-'):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
     f.write(data);f.flush();info=subprocess.check_output(['pdfinfo',f.name],text=True,stderr=subprocess.DEVNULL)
     if 'Encrypted:       yes' in info:raise ValueError('Encrypted PDF excluded')
     text=subprocess.check_output(['pdftotext',f.name,'-'],text=True,stderr=subprocess.DEVNULL)
    validate_text(text,row['name']);fmt='pdf';pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1]);content=data
   else:
    source=data.decode('utf-8',errors='replace');parser=Links();parser.feed(source)
    if depth<2:
     extra=[]
     for label,href in parser.rows:
      target=urljoin(resolved,href);bits=(label+' '+target).lower()
      if urlsplit(target).hostname!=urlsplit(resolved).hostname:continue
      if any(x in bits for x in ['constitution','constitu','const.htm','conart']) and not any(x in bits for x in ['history','historic','amendmentpropos','proposed']):
       if '.pdf' in target.lower() or any(x in label.lower() for x in ['full','complete','entire','text','download']):extra.append((target,depth+1))
     queue=extra[:6]+queue
    body,text=body_copy(data,resolved)
    if urlsplit(resolved).hostname=='50constitutions.org':
     body,text,count,snapshot=university_body(source);record['provisions']=count;record['source_snapshot_request']=snapshot
    validate_text(text,row['name']);fmt='html';pages=None
    content=('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(row['name'])+' — constitutional text</title><link rel="stylesheet" href="/assets/css/ark-pages.css"></head><body><main class="ark-page"><a class="ark-page-brand" href="/">Data Ark</a><nav><a href="index.html">Jurisdiction coverage</a></nav><h1>'+html.escape(row['name'])+'</h1><p>Publisher constitutional/charter text snapshot. Retrieved '+record['checked_at']+'. Text-only presentation; external links require internet. No guarantee of later amendments or legal currency. ' + html.escape(row.get('fallback_attribution','')) + ' <a href="'+html.escape(resolved,quote=True)+'">Publisher source</a></p>'+body+'</main></body></html>').encode()
   name=row['id']+'.'+fmt;atomic(DEST/name,content)
   record.update(status='installed',filename=name,format=fmt,pages=pages,source_url=url,resolved_url=resolved,bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),scope='Constitution/charter document snapshot; not complete statutes, regulations or case law')
   print('installed',row['name'],len(content),flush=True);return record
  except Exception as e:record['attempts'].append({'url':url,'error':str(e)})
 record['error']=record['attempts'][-1]['error'] if record['attempts'] else 'No direct verified public document configured'
 print('unavailable',row['name'],record['error'],flush=True);return record

def publish(records):
 from tools.install_resilience import atomic
 e=html.escape;size=sum(r.get('bytes',0) for r in records)
 pieces=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>U.S. jurisdiction coverage — Data Ark</title><link rel="stylesheet" href="/assets/css/ark-pages.css"></head><body><main class="ark-page"><a class="ark-page-brand" href="/">Data Ark</a><nav><a href="../index.html">Laws and codes</a></nav><h1>State and territorial legal coverage</h1><p>All 50 states, the District of Columbia and five inhabited U.S. territories. A jurisdiction entry does not mean its entire body of law is installed. Constitutions and charters are compact; complete statute, regulation and municipal collections require separate publisher-specific acquisition.</p><p>'+str(sum(r['status']=='installed' for r in records))+' verified constitutional/charter documents · '+str(round(size/1024**2,1))+' MiB. Failed downloads remain explicit gaps. Existing Massachusetts chapters and the U.S. Code remain available in the parent collection.</p>']
 for r in records:
  pieces.append('<section><h2>'+e(r['name'])+'</h2>')
  if r['status']=='installed':pieces.append('<p><a href="'+e(r['filename'],quote=True)+'">Read offline '+e(r.get('document_kind','constitution'))+'</a> · '+str(round(r['bytes']/1024**2,2))+' MiB</p><p>'+e(r['scope'])+'</p><small>Retrieved '+e(r['checked_at'])+' · SHA-256 '+r['sha256']+'</small>')
  elif r['status']=='framework-only':pieces.append('<p><a href="'+e(r['framework_url'],quote=True)+'">Read local federal territorial framework (Title 48)</a></p><p>'+e(r['scope'])+'</p>')
  else:pieces.append('<p>Constitution/charter not installed: '+e(r.get('error','Not acquired'))+'</p>')
  pieces.append('<p>Complete statutes: not installed through this collection.</p>')
  if r.get('statute_source'):pieces.append('<details><summary>Online statute source</summary><a href="'+e(r['statute_source'],quote=True)+'">Publisher website — internet required</a></details>')
  pieces.append('</section>')
 pieces.append('<p><a href="sources.json">Sources, hashes, and download failures</a></p></main></body></html>')
 atomic(DEST/'index.html',''.join(pieces).encode());atomic(DEST/'sources.json',(json.dumps(records,indent=2)+'\n').encode())

def register(records):
 from app.services.manifest import load_manifest,atomic_write
 from tools.library_removal import serialize
 import fcntl
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);manifest=load_manifest(ROOT/'dataark.yaml')
  repo=next(r for r in manifest['repositories'] if r['id']=='civic-reference')
  repo['description']='Federal statutes, state and territorial constitutional snapshots, and clearly scoped legal references.'
  if not any(x.get('url')=='/library-files/civic-reference/jurisdictions/index.html' for x in repo['links']):repo['links'].append({'title':'State and territorial coverage','url':'/library-files/civic-reference/jurisdictions/index.html'})
  for r in records:
   if r['status']!='installed':continue
   asset={'id':'jurisdiction-'+r['id'],'repository_id':'civic-reference','category':'pdf_reference','title':r['name']+' — '+r.get('document_kind','constitutional text')+' (snapshot)','relative_path':'civic-reference/jurisdictions/'+r['filename'],'service_endpoint':'/library-files/civic-reference/jurisdictions/'+r['filename'],'online_url':r['source_url'],'download_url':r['source_url'],'expected_hash':r['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':r['scope']+'; retrieved '+r['checked_at']}
   manifest['assets']=[x for x in manifest['assets'] if x['id']!=asset['id']]+[asset]
  atomic_write(ROOT/'dataark.yaml',serialize(manifest).encode())

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--acquire',action='store_true');args=parser.parse_args()
 config=json.loads((ROOT/'deploy/reference/jurisdictions.json').read_text())
 if not args.acquire:print(json.dumps(config,indent=2));return
 if any(not re.fullmatch(r'[a-z0-9_-]+',r['id']) for r in config['jurisdictions']):raise SystemExit('Unsafe jurisdiction ID')
 if len({r['id'] for r in config['jurisdictions']})!=len(config['jurisdictions']):raise SystemExit('Duplicate jurisdiction IDs')
 if not Path('/mnt/storage').is_mount():raise SystemExit('Content SSD not mounted')
 DEST.mkdir(parents=True,exist_ok=True)
 previous={r['id']:r for r in json.loads((DEST/'sources.json').read_text())} if (DEST/'sources.json').is_file() else {}
 records=[]
 for row in config['jurisdictions']:
  old=previous.get(row['id']);file=DEST/old.get('filename','') if old else None
  if old and old['status']=='installed' and file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==old['sha256']:records.append(old)
 todo=[r for r in config['jurisdictions'] if r['id'] not in {x['id'] for x in records}]
 with concurrent.futures.ThreadPoolExecutor(max_workers=config['policy']['workers']) as pool:records+=list(pool.map(acquire,todo))
 if sum(r.get('bytes',0) for r in records)>config['policy']['max_total_gib']*1024**3:raise SystemExit('Configured total collection cap exceeded; not registered')
 records.sort(key=lambda r:r['name']);publish(records);register(records)
 print('Installed',sum(r['status']=='installed' for r in records),'of',len(records),'jurisdictions; total bytes',sum(r.get('bytes',0) for r in records),flush=True)
if __name__=='__main__':main()
