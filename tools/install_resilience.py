#!/usr/bin/env python3
"""Explicit offline resilience/legal catalogue installer. No credentials or private documents.
Run /usr/bin/python3 tools/install_resilience.py --register, then deploy/deploy-web.sh.
"""
import argparse,concurrent.futures,hashlib,html,json,re,subprocess,sys,tempfile,urllib.request,zipfile
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));MOUNT=Path('/mnt/storage')
UA='Mozilla/5.0 (Data Ark offline public reference library)'
STYLE='body{font:18px/1.65 system-ui;max-width:1050px;margin:25px auto;padding:0 20px;background:#faf8f2;color:#203d43}a{color:#075d89}h1,h2,h3{line-height:1.3}p,li{overflow-wrap:anywhere}table{border-collapse:collapse;max-width:100%;display:block;overflow:auto}td,th{padding:6px;border:1px solid #b6c6c0}.source{padding:15px;background:#e6eee6;border:1px solid #a6b8ae}li{margin:12px 0}small{display:block}summary{cursor:pointer;padding:10px}header{margin:30px 0}input{font:inherit;padding:10px;width:100%;max-width:600px}section{padding:20px 0;border-bottom:1px solid #aabbb4}'
def now():return datetime.now(timezone.utc).isoformat()
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:f.write(data);p=Path(f.name)
 p.chmod(0o644);p.replace(path)
def fetch(url,limit=40*1024**2):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=40) as r:
  data=r.read(limit+1);resolved=r.url
 if len(data)>limit:raise ValueError('Publisher file exceeds size cap')
 return data,resolved
class TextCopy(HTMLParser):
 def __init__(self,base):super().__init__(convert_charrefs=True);self.base=base;self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style','form','nav','iframe','object','svg'):self.skip+=1;return
  if self.skip:return
  if t in ['h1','h2','h3','h4','p','ul','ol','li','table','tr','td','th','blockquote','strong','em','br','pre']:self.parts.append('<'+t+'>')
  elif t=='a':
   u=urljoin(self.base,dict(a).get('href',''))
   if urlsplit(u).scheme in ['http','https']:self.parts.append('<a rel="noreferrer" href="'+html.escape(u,quote=True)+'">')
 def handle_endtag(self,t):
  if t in ('script','style','form','nav','iframe','object','svg'):
   if self.skip:self.skip-=1
   return
  if not self.skip and t in ['h1','h2','h3','h4','p','ul','ol','li','table','tr','td','th','blockquote','strong','em','pre','a']:self.parts.append('</'+t+'>')
 def handle_data(self,d):
  if not self.skip:self.parts.append(html.escape(d))
def body_copy(data,url):
 text=data.decode('utf-8',errors='replace');main=re.search(r'<main\b[^>]*>(.*?)</main>',text,re.S|re.I)
 if main:text=main[1]
 else:
  body=re.search(r'<body\b[^>]*>(.*?)</body>',text,re.S|re.I)
  if body:text=body[1]
 parser=TextCopy(url);parser.feed(text);body=''.join(parser.parts)
 plain=' '.join(re.sub('<[^>]+>',' ',html.unescape(body)).split())
 minimum=40 if urlsplit(url).hostname=='malegislature.gov' else 250
 if len(plain)<minimum or any(x in plain[:700].lower() for x in ['access denied','request blocked','enable javascript and cookies']):raise ValueError('No substantive public text found')
 return body,plain
def document(title,body,url,edition):
 e=html.escape
 return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+'</title><style>'+STYLE+'</style></head><body><nav><a href="/">Data Ark library</a> · <a href="../index.html">Collection</a></nav><h1>'+e(title)+'</h1><div class="source">'+e(edition)+'<br>Text-only offline presentation; external links require internet. Images, video, dynamic search and navigation are not archived.<br>Retrieved '+now()+' · <a href="'+e(url,quote=True)+'">Original publisher page (internet)</a></div>'+body+'</body></html>').encode()
def previous(item,path,error):
 record=MOUNT/item['collection']/'sources.json'
 if record.is_file() and path.is_file():
  old=next((r for r in json.loads(record.read_text()) if r['id']==item['id'] and r.get('sha256')==hashlib.sha256(path.read_bytes()).hexdigest()),None)
  if old:return {**old,'checked_at':now(),'last_check_error':str(error)}
 return {**item,'status':'unavailable','error':str(error),'checked_at':now()}
def download(item):
 item=dict(item);path=MOUNT/item['collection']/'documents'/(item['id']+'.'+item['format']);item['filename']='documents/'+path.name;item['checked_at']=now()
 try:
  data,resolved=fetch(item['url']);item['resolved_url']=resolved
  if item['format']=='pdf':
   if not data.startswith(b'%PDF-'):raise ValueError('Publisher did not return a PDF')
   with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
    f.write(data);f.flush();info=subprocess.check_output(['pdfinfo',f.name],text=True,stderr=subprocess.STDOUT);item['pages']=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
    text=subprocess.check_output(['pdftotext','-f','1','-l','2',f.name,'-'],text=True,stderr=subprocess.DEVNULL)
   if re.search(r'PROPOSED AMENDMENTS|DRAFT FOR',text,re.I) and not item.get('allow_draft'):raise ValueError('Proposed/draft document excluded from adopted-code collection')
   item['document_header']=' '.join(text.split())[:600]
  else:
   body,plain=body_copy(data,item['url']);item['document_header']=plain[:600];data=document(item['title'],body,item['url'],item['edition'])
  atomic(path,data);item.update(status='installed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as error:item=previous(item,path,error)
 print(item['status'],item['id'],item.get('error',''),flush=True);return item
def chapter(url,number,title):
 item={'id':'ma-chapter-'+number,'collection':'civic-reference','group':'Massachusetts law','title':'Massachusetts General Laws Chapter '+number+' — '+title,'url':url,'format':'html','edition':'Unofficial legislature sections captured at retrieval','note':'Selected chapter only; other General Laws, session laws, orders and case law are not included.'};item['filename']='documents/'+item['id']+'.html';path=MOUNT/'civic-reference'/item['filename']
 try:
  data,_=fetch(url);text=data.decode();links=list(dict.fromkeys(urljoin(url,u) for u in re.findall(r'href="([^"]*'+re.escape('/Chapter'+number+'/Section')+r'[^"?#]+)"',text,re.I)))
  if not links or len(links)>250:raise ValueError('Unexpected chapter section count')
  def section(u):
   try:
    d,_=fetch(u);body,plain=body_copy(d,u);return u,body,None
   except Exception as e:return u,None,str(e)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:sections=list(pool.map(section,links))
  bodies=[];failed=[]
  for u,body,error in sections:
   if error:failed.append({'url':u,'error':error})
   else:bodies.append('<section><p><a href="'+html.escape(u,quote=True)+'">'+html.escape(u.rsplit('/',1)[-1])+' — original source (internet)</a></p>'+body+'</section>')
  if not bodies:raise ValueError('No sections could be archived')
  item['coverage']=str(len(bodies))+'/'+str(len(links))+' listed sections retrieved';item['missing_sections']=failed
  data=document(item['title'],'<p class="source">'+item['coverage']+'. '+('Some sections are missing; see collection source record.' if failed else '')+'</p>'+''.join(bodies),url,item['edition']);atomic(path,data);item.update(status='installed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),checked_at=now())
 except Exception as error:item=previous(item,path,error)
 print(item['status'],item['id'],item.get('coverage',item.get('error','')),flush=True);return item
def us_code():
 folder=MOUNT/'civic-reference';archive=folder/'us-code-source.zip';meta_path=folder/'us-code-source.json'
 if not archive.is_file() or not meta_path.is_file():
  source='https://uscode.house.gov/download.html';page,_=fetch(source);text=page.decode();match=re.search(r'href="([^"]*htm_uscAll[^"]+\.zip)"',text)
  if not match:raise RuntimeError('No official XHTML bulk archive found')
  url=urljoin(source,match[1]);payload,resolved=fetch(url,250*1024**2);currency=re.findall(r'Public Law[^<]{0,100}',text)[:3]
  if not payload.startswith(b'PK'):raise RuntimeError('Publisher did not return a ZIP')
  atomic(archive,payload);atomic(meta_path,json.dumps({'source_page':source,'url':url,'resolved_url':resolved,'currency':currency,'sha256':hashlib.sha256(payload).hexdigest(),'retrieved_at':now()},indent=2).encode())
 meta=json.loads(meta_path.read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['sha256'],'US Code source checksum mismatch';records=[];links=[];currency=meta['currency'][0].strip().rstrip('.')
 with zipfile.ZipFile(archive) as z:
  if sum(i.file_size for i in z.infolist())>1024**3:raise RuntimeError('Expanded Code exceeds cap')
  for member in z.infolist():
   if not re.fullmatch(r'[A-Za-z0-9_-]+\.(htm|html)',member.filename):continue
   data=z.read(member);text=data.decode('utf-8',errors='replace');match=re.search(r'AUTHORITIES-USC-TITLE-NAME:(.*?)-->',text,re.S);title=html.unescape(match[1].strip()) if match else member.filename
   # Publisher text and anchors are retained; external executable resources are not.
   text=re.sub(r'<script\b.*?</script>','',text,flags=re.S|re.I);text=re.sub(r'<link\b[^>]*>','',text,flags=re.I);text=text.replace('</head>','<style>'+STYLE+'</style></head>');notice='<div class="source"><a href="../index.html">U.S. Code title index</a><br>Official OLRC release snapshot: '+html.escape(currency)+'. Preliminary release; verify later amendments. Large titles may be slow on a phone.</div>';text=re.sub(r'(<body\b[^>]*>)',r'\1'+notice,text,count=1,flags=re.I);out=text.encode();path=folder/'us-code'/member.filename;atomic(path,out)
   item={'id':'usc-'+member.filename.removesuffix('.htm').lower(),'collection':'civic-reference','group':'Federal law','title':'United States Code — '+title,'url':meta['url'],'format':'html','filename':'us-code/'+member.filename,'edition':currency,'note':'Official bulk-release text, offline formatting. Not regulations, case law, uncodified laws or later amendments. Use browser Find within a title.','checked_at':now(),'status':'installed','bytes':len(out),'sha256':hashlib.sha256(out).hexdigest()};records.append(item)
   links.append('<li><a href="'+html.escape(member.filename,quote=True)+'">'+html.escape(title)+'</a> — '+str(round(len(out)/1024**2,1))+' MiB</li>')
 atomic(folder/'us-code/index.html',('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>U.S. Code — offline title index</title><style>'+STYLE+'</style></head><body><a href="../index.html">Laws & codes</a><h1>United States Code</h1><p>'+html.escape(currency)+' · '+str(len(records))+' publisher title/appendix files.</p><p>Use browser Find within a title. Some titles are large; downloading to a capable device may work better than opening on a low-memory phone. This is statutory text, not the complete body of federal law.</p><ul>'+''.join(links)+'</ul></body></html>').encode())
 records.append({'id':'usc-source-archive','collection':'civic-reference','group':'Federal law','title':'U.S. Code — original full publisher XHTML ZIP','url':meta['url'],'format':'zip','filename':'us-code-source.zip','edition':currency,'note':'Unmodified official bulk archive; extract on your device.','checked_at':now(),'status':'installed','bytes':archive.stat().st_size,'sha256':meta['sha256']})
 print('US Code:',len(records)-1,'title/appendix files',flush=True);return records
def index(collection,records):
 e=html.escape;title='Wilderness, Off-grid Power & Field References' if collection=='resilience' else 'Laws, Regulations & Codes';p=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+STYLE+'</style></head><body><nav><a href="/">Library</a> · <a href="/power.html">Power planner</a> · <a href="/pdf-forms.html">Fill a PDF</a> · <a href="/callsigns.html">Amateur callsigns</a></nav><header><h1>'+title+'</h1><p>Stored locally on the Ark. Source editions, snapshot dates and gaps are part of the catalogue.</p></header>']
 if collection=='civic-reference':p.append('<div class="source"><strong>Coverage:</strong> the official U.S. Code release, a pocket Constitution, selected CFR volumes, selected Massachusetts chapters, state constitutions/code sources and available local-law material. This is not every law, regulation, decision or emergency order. Retrieval date does not establish that a text is currently in force. Model-code books referenced by Massachusetts amendments are not included unless separately lawfully obtained. <a href="us-code/index.html">Browse the U.S. Code by title</a>.</div>')
 else:p.append('<div class="source">Read publisher cautions and practice skills before relying on them. Technical fundamentals, consumer planning references and historical manuals are labeled; they are not current electrical designs or a replacement for first-aid training. <a href="/power.html">Offline load, battery, solar and hydro estimates</a>.</div>')
 p.append('<p><label>Find a title or topic <input id="reference-search" type="search"></label></p>')
 for group in dict.fromkeys(r['group'] for r in records):
  p.append('<section id="'+re.sub(r'[^a-z0-9]+','-',group.lower()).strip('-')+'" data-reference-section><h2>'+e(group)+'</h2><ul>')
  group_records=[r for r in records if r['group']==group and r['status']=='installed']
  if group=='Federal law':p.append('<p>The full U.S. Code title list is also available in its <a href="us-code/index.html">dedicated index</a>. The entries below are individual local files.</p>')
  if not group_records:p.append('<p>No verified local files in this group yet.</p>')
  for r in group_records:
   p.append('<li data-reference data-form-id="ref-'+e(r['id'].lower(),quote=True)+'" data-search="'+e((r['title']+' '+r['note']).lower(),quote=True)+'"><a data-form-file href="'+e(r['filename'],quote=True)+'">'+e(r['title'])+'</a><small>'+e(r['edition'])+' · '+r['format'].upper()+((' · '+str(r['pages'])+' pages') if r.get('pages') else '')+' · '+str(round(r['bytes']/1024**2,2))+' MiB</small><small>'+e(r['note']+' '+r.get('coverage',''))+'</small><details><summary>Source and retrieval</summary><p>'+e(r.get('document_header',''))+'</p><p>Retrieved '+e(r['checked_at'])+' from <a href="'+e(r['url'],quote=True)+'">publisher (internet)</a>.</p></details></li>')
  p.append('</ul></section>')
 missing=[r for r in records if r['status']!='installed']
 if missing:
  p.append('<section><h2>Not installed / publisher unavailable</h2><ul>')
  for r in missing:p.append('<li>'+e(r['title'])+' — '+e(r['error'])+'<small>'+e(r['note'])+'</small><a href="'+e(r['url'],quote=True)+'">Original source (internet)</a></li>')
  p.append('</ul></section>')
 p.append('<footer><a href="sources.json">Source records, hashes and coverage</a> · <a href="/docs/20-Administration/ResilienceResources.html">Maintenance & remaining gaps</a></footer><script src="/assets/js/forms-availability.js"></script><script src="/assets/js/reference-search.js?v=20261023-resilience1"></script></body></html>');atomic(MOUNT/collection/'index.html',''.join(p).encode())
def register(records):
 import fcntl
 from app.services.manifest import load_manifest,atomic_write
 from tools.library_removal import serialize
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);data=load_manifest(ROOT/'dataark.yaml')
  for key,title,desc,links in [('resilience','Wilderness Survival & Off-grid Power','Outdoor survival, navigation, energy planning and generator references with source editions.',[{'title':'Read local field & power references','url':'/library-files/resilience/index.html'},{'title':'Offline power calculators','url':'/power.html'}]),('civic-reference','Laws, Regulations & Codes','Official federal statute snapshot and clearly scoped Massachusetts/local legal and code references.',[{'title':'Browse local laws & code coverage','url':'/library-files/civic-reference/index.html'},{'title':'U.S. Code title index','url':'/library-files/civic-reference/us-code/index.html'},{'title':'Fill PDF forms locally','url':'/pdf-forms.html'},{'title':'Amateur callsign search','url':'/callsigns.html'}])]:
   repo={'id':key,'title':title,'description':desc,'category':'content_sources','collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':links};data['repositories']=[r for r in data['repositories'] if r['id']!=key]+[repo]
  for r in records:
   if r['status']!='installed':continue
   identifier='ref-'+r['id'].lower();asset={'id':identifier,'repository_id':r['collection'],'category':'pdf_reference','title':r['title'],'relative_path':r['collection']+'/'+r['filename'],'service_endpoint':'/library-files/'+r['collection']+'/'+r['filename'],'online_url':r['url'],'download_url':r['url'],'expected_hash':r['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':r['edition']+'; '+r['note']+'; retrieved '+r['checked_at']};data['assets']=[a for a in data['assets'] if a['id']!=identifier]+[asset]
  atomic_write(ROOT/'dataark.yaml',serialize(data).encode())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--register',action='store_true');a=p.parse_args()
 if not MOUNT.is_mount():raise SystemExit('Content SSD must be mounted')
 catalogue=json.loads((ROOT/'deploy/reference/resilience-catalogue.json').read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(download,catalogue))
 for entry in json.loads((ROOT/'deploy/reference/resilience-settings.json').read_text())['massachusetts_chapters']:records.append(chapter(entry['url'],entry['number'],entry['title']))
 records+=us_code()
 for collection in ['resilience','civic-reference']:
  rows=[r for r in records if r['collection']==collection];atomic(MOUNT/collection/'sources.json',(json.dumps(rows,ensure_ascii=False,indent=2)+'\n').encode());index(collection,rows)
 if a.register:register(records)
 from tools.publish_content import publish
 publish(MOUNT);print('Installed',sum(r['status']=='installed' for r in records),'of',len(records),'reference files',flush=True)
if __name__=='__main__':main()
