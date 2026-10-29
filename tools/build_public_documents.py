#!/usr/bin/env python3
"""Build matching offline and public document editions from repository sources.
Public uploads contain only generated HTML/PDF and publication metadata.
"""
from pathlib import Path
import argparse,hashlib,html,json,re,shutil,subprocess,sys
from urllib.parse import urlsplit,urlunsplit
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.publish_docs import markdown_to_html

def build(website=None):
 c=yaml.safe_load((ROOT/'config/documentation.yaml').read_text(encoding='utf-8-sig'))
 assert c['schema']==1 and c['update_policy']=='bundled-with-software'
 if c['supported_bootstrap_released']:raise ValueError('A supported bootstrap needs a reviewed release implementation, not only a flag.')
 pages=c['pages'];labels={'collection':'Collection','features':'Features','engineering':'Engineering','bootstrap':'Bootstrap','installation':'Installation','handbook':'Handbook'};sources={str((ROOT/p['source']).resolve()):p['id'] for p in pages}
 fingerprints={}
 for p in pages:
  assert re.fullmatch('[a-z][a-z-]+',p['id'])
  for name in [p['source']]+([p['pdf']] if p.get('pdf') else []):fingerprints[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
 fingerprints['config/documentation.yaml']=hashlib.sha256((ROOT/'config/documentation.yaml').read_bytes()).hexdigest()
 fingerprints['tools/build_public_documents.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 revision=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 edition=c['publication_date']+'-'+hashlib.sha256(json.dumps({'inputs':fingerprints,'revision':revision},sort_keys=True).encode()).hexdigest()[:10]
 local=ROOT/'app/static/about';local.mkdir(exist_ok=True)
 if website:
  website=Path(website);web=website/'data-ark';web.mkdir(exist_ok=True)
  archive=web/'editions'/edition;archive.mkdir(parents=True,exist_ok=True)
 def url_for(page,online,pinned=False):return ('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+page+'/' if online else '/about/'+page+'/'
 def links(page,body,online,pinned=False):
  def replace(m):
   value=html.unescape(m.group(1));u=urlsplit(value)
   if u.scheme or u.netloc:return m.group(0)
   if u.path.endswith('.pdf'):
    name=Path(u.path).name
    if name in ['collection-catalogue.pdf','feature-catalogue.pdf']:
     value=('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+name if online else '/'+name
   elif u.path.endswith('.html') or u.path.endswith('.md'):
    source=(ROOT/page['source']).parent/u.path;key=str(source.with_suffix('.md').resolve())
    if key in sources:value=url_for(sources[key],online,pinned)
    elif key.startswith(str((ROOT/'docs').resolve())):
     rel=Path(key).relative_to(ROOT/'docs').as_posix()
     value='https://github.com/DavJenkins/pharos/blob/'+revision+'/docs/'+rel if online else '/docs/'+str(Path(rel).with_suffix('.html')).replace('\\','/')
    elif online and u.path.startswith('/'):value='http://dataark'+u.path
   return 'href="'+html.escape(value+('#'+u.fragment if u.fragment and '#' not in value else ''),quote=True)+'"'
  return re.sub(r'href="([^"]+)"',replace,body)
 for p in pages:
  rendered=markdown_to_html((ROOT/p['source']).read_text(encoding='utf-8-sig'))
  body=re.search(r'<main[^>]*>(.*?)</main>',rendered,re.S).group(1)
  body=re.sub(r'^<p class="docs-eyebrow">.*?</p>','',body,count=1)
  body=re.sub(r'<p>\*(.*?)\*</p>',r'<p><em>\1</em></p>',body)
  nav=''.join('<a href="'+url_for(v['id'],False)+'">'+html.escape(labels[v['id']])+'</a>' for v in pages)
  offline=rendered.replace('<title>Data Ark Documentation</title>','<title>'+html.escape(p['title'])+'</title>').replace(re.search(r'<main[^>]*>.*?</main>',rendered,re.S).group(0),'<main class="docs-paper handbook-paper"><nav aria-label="Ark publications">'+nav+'</nav><p class="docs-eyebrow">INSTALLED SOFTWARE EDITION · '+edition+'</p>'+links(p,body,False)+'</main>')
  dest=local/p['id'];dest.mkdir(exist_ok=True);(dest/'index.html').write_text(offline,encoding='utf-8')
  if website:
   for target,pinned in [(web/p['id'],False),(archive/p['id'],True)]:
    target.mkdir(exist_ok=True)
    nav=''.join('<a href="'+url_for(v['id'],True,pinned)+'">'+html.escape(labels[v['id']])+'</a>' for v in pages)
    pagebody=links(p,body,True,pinned)
    pdf=p.get('pdf');download='<p><a class="button" href="'+('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+Path(pdf).name+'">Download PDF ↓</a></p>' if pdf else ''
    public='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(p['title'])+' | DEJ Software</title><link rel="canonical" href="'+c['website_base']+url_for(p['id'],True,pinned)+'"><link rel="stylesheet" href="/styles.css"></head><body><a class="skip" href="#main">Skip to content</a><header class="wrap"><p><a href="/#pharos">← Pharos Data Ark</a></p><nav class="ark-document-nav" aria-label="Ark publications">'+nav+'</nav></header><main id="main" class="wrap collection-document"><p class="eyebrow">PHAROS DATA ARK · '+edition+'</p>'+download+pagebody+'<p class="collection-edition">Generated from the Ark repository. <a href="/data-ark/editions/'+edition+'/'+p['id']+'/">Permanent edition</a> · <a href="/data-ark/publication.json">Publication checksums</a></p></main><footer class="wrap footer"><p>DEJ Software · Practical Software for Real Life</p><a href="/#pharos">Back to Pharos Data Ark</a></footer></body></html>'
    (target/'index.html').write_text(public,encoding='utf-8')
   if pdf:
    for folder in [web,archive]:shutil.copyfile(ROOT/pdf,folder/Path(pdf).name)
 meta={'schema':1,'edition':edition,'source_revision':revision,'source_revision_note':'Repository HEAD at build; source_sha256 identifies the exact publication inputs.','update_policy':c['update_policy'],'supported_bootstrap_released':False,'source_sha256':fingerprints,'pages':[{**p,'local_permalink':url_for(p['id'],False),'website_permalink':url_for(p['id'],True)} for p in pages]}
 (local/'publication.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
 if website:
  for folder in [web,archive]:(folder/'publication.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
  # Retain already advertised public URLs as small canonical redirects.
  (website/'data-ark-collection.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/data-ark/collection/"><title>The Data Ark collection</title><link rel="canonical" href="'+c['website_base']+'/data-ark/collection/"><p><a href="/data-ark/collection/">Read the Data Ark collection catalogue</a></p></html>',encoding='utf-8')
  shutil.copyfile(ROOT/'app/static/collection-catalogue.pdf',website/'data-ark-collection-catalogue.pdf')
 print('Built',len(pages),'paired documents;',edition)
 return meta
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--website',type=Path);a=parser.parse_args();build(a.website)
