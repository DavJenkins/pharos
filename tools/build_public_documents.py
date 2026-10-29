#!/usr/bin/env python3
"""Build matching offline and public document editions from repository sources.
Public uploads contain only generated HTML/PDF and publication metadata.
"""
from pathlib import Path
import argparse,hashlib,html,json,re,shutil,subprocess,sys
from urllib.parse import urlsplit,urlunsplit
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def input_digest(path):
 path=Path(path)
 content=path.read_bytes() if path.suffix=='.pdf' else path.read_text(encoding='utf-8-sig').encode('utf-8')
 return hashlib.sha256(content).hexdigest()
from tools.publish_docs import markdown_to_html
from tools import public_handbook, public_downloads

def build(website=None):
 c=yaml.safe_load((ROOT/'config/documentation.yaml').read_text(encoding='utf-8-sig'))
 assert c['schema']==1 and c['update_policy']=='bundled-with-software'
 if c['supported_bootstrap_released']:raise ValueError('A supported bootstrap needs a reviewed release implementation, not only a flag.')
 pages=c['pages'];labels={'collection':'Collection','features':'Features','engineering':'Engineering','bootstrap':'Bootstrap','installation':'Installation','handbook':'Handbook'};sources={str((ROOT/p['source']).resolve()):p['id'] for p in pages}
 fingerprints={}
 for p in pages:
  assert re.fullmatch('[a-z][a-z-]+',p['id'])
  for name in [p['source']]+([p['pdf']] if p.get('pdf') else []):fingerprints[name]=input_digest(ROOT/name)
 for path in public_handbook.inputs(ROOT):fingerprints[path.relative_to(ROOT).as_posix()]=input_digest(path)
 for name in ['tools/publish_docs.py','tools/public_downloads.py','tools/package_document_downloads.py',c['download_history']]:fingerprints[name]=input_digest(ROOT/name)
 fingerprints['tools/public_handbook.py']=input_digest(ROOT/'tools/public_handbook.py')
 fingerprints['config/documentation.yaml']=input_digest(ROOT/'config/documentation.yaml')
 fingerprints['tools/build_public_documents.py']=input_digest(Path(__file__))
 revision=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 edition=c['publication_date']+'-'+hashlib.sha256(json.dumps({'inputs':fingerprints,'revision':revision},sort_keys=True).encode()).hexdigest()[:10]
 local=ROOT/'app/static/about';local.mkdir(exist_ok=True)
 if website:
  website=Path(website);web=website/'data-ark';web.mkdir(exist_ok=True)
  archive=ROOT/'output/document-download-staging/data-ark/editions'/edition;archive.mkdir(parents=True,exist_ok=True)
 def url_for(page,online,pinned=False):return ('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+page+'/' if online else '/about/'+page+'/'
 def links(page,body,online,pinned=False):
  prefix='/data-ark/editions/'+edition+'/' if pinned else '/data-ark/'
  selected={key:url_for(value,online,pinned) for key,value in sources.items()}
  return public_handbook.rewrite(ROOT,(ROOT/page['source']).resolve(),body,prefix,local=not online,selected=selected)
 for p in pages:
  rendered=markdown_to_html((ROOT/p['source']).read_text(encoding='utf-8-sig'))
  body=re.search(r'<main[^>]*>(.*?)</main>',rendered,re.S).group(1)
  body=re.sub(r'^<p class="docs-eyebrow">.*?</p>','',body,count=1)
  body=re.sub(r'<p>\*(.*?)\*</p>',r'<p><em>\1</em></p>',body)
  nav=''.join('<a href="'+('/docs/SUMMARY.html' if v['id']=='handbook' else url_for(v['id'],False))+'">'+html.escape(labels[v['id']])+'</a>' for v in pages)
  offline=rendered.replace('<title>Data Ark Documentation</title>','<title>'+html.escape(p['title'])+'</title>').replace(re.search(r'<main[^>]*>.*?</main>',rendered,re.S).group(0),'<main class="docs-paper handbook-paper"><nav aria-label="Ark publications">'+nav+'</nav><p class="docs-eyebrow">INSTALLED SOFTWARE EDITION · '+edition+'</p>'+links(p,body,False)+'</main>')
  dest=local/p['id'];dest.mkdir(exist_ok=True);(dest/'index.html').write_text(offline,encoding='utf-8')
  if website:
   for target,pinned in [(web/p['id'],False),(archive/p['id'],True)]:
    target.mkdir(exist_ok=True)
    nav=''.join('<a href="'+(('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+'docs/' if v['id']=='handbook' else url_for(v['id'],True,pinned))+'">'+html.escape(labels[v['id']])+'</a>' for v in pages)
    pagebody=links(p,body,True,pinned)
    pdf=p.get('pdf');download='<p><a class="button" href="'+('/data-ark/editions/'+edition+'/' if pinned else '/data-ark/')+Path(pdf).name+'">Download PDF ↓</a></p>' if pdf else ''
    public='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(p['title'])+' | DEJ Software</title><link rel="canonical" href="'+c['website_base']+url_for(p['id'],True,pinned)+'"><link rel="stylesheet" href="/styles.css"></head><body><a class="skip" href="#main">Skip to content</a><header class="wrap"><p><a href="/#pharos">← Pharos Data Ark</a></p><nav class="ark-document-nav" aria-label="Ark publications">'+nav+'</nav></header><main id="main" class="wrap collection-document"><p class="eyebrow">PHAROS DATA ARK · '+edition+'</p>'+download+pagebody+'<p class="collection-edition">Generated from the Ark repository. <a href="/data-ark/editions/'+edition+'/'+p['id']+'/">Permanent edition</a> · <a href="/data-ark/publication.json">Publication checksums</a></p></main><footer class="wrap footer"><p>DEJ Software · Practical Software for Real Life</p><a href="/#pharos">Back to Pharos Data Ark</a></footer></body></html>'
    (target/'index.html').write_text(public,encoding='utf-8')
   if pdf:
    for folder in [archive]:shutil.copyfile(ROOT/pdf,folder/Path(pdf).name)
 meta={'schema':1,'edition':edition,'source_revision':revision,'source_revision_note':'Repository HEAD at build; source_sha256 identifies the exact publication inputs.','update_policy':c['update_policy'],'supported_bootstrap_released':False,'text_hash_normalization':'UTF-8 without BOM, with LF line endings; PDF hashes use original bytes','source_sha256':fingerprints,'pages':[{**p,'local_permalink':url_for(p['id'],False),'website_permalink':url_for(p['id'],True)} for p in pages]}
 (local/'publication.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
 if website:
  def frame(title,body,path,prefix):
   nav=''.join('<a href="'+(prefix+'docs/' if p['id']=='handbook' else prefix+p['id']+'/')+'">'+html.escape(labels[p['id']])+'</a>' for p in pages)+'<a href="'+prefix+'api/">API</a>'
   return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' | DEJ Software</title><link rel="canonical" href="'+c['website_base']+path+'"><link rel="stylesheet" href="/styles.css"></head><body><a class="skip" href="#main">Skip to content</a><header class="wrap"><p><a href="/#pharos">← Pharos Data Ark</a></p><nav class="ark-document-nav" aria-label="Ark documentation">'+nav+'</nav></header><main id="main" class="wrap collection-document"><p class="eyebrow">PHAROS DATA ARK · '+edition+'</p>'+body+'</main><footer class="wrap footer"><p>DEJ Software · Practical Software for Real Life</p><a href="'+prefix+'docs/">Handbook contents</a></footer></body></html>'
  count=public_handbook.publish(ROOT,web,archive,edition,c,frame)
  meta['handbook_documents']=count;meta['handbook_permalink']='/data-ark/docs/';meta['api_permalink']='/data-ark/api/'
  (local/'publication.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
  for folder in [web,archive]:(folder/'publication.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
  # Retain already advertised public URLs as small canonical redirects.
  (website/'data-ark-collection.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/data-ark/collection/"><title>The Data Ark collection</title><link rel="canonical" href="'+c['website_base']+'/data-ark/collection/"><p><a href="/data-ark/collection/">Read the Data Ark collection catalogue</a></p></html>',encoding='utf-8')
  public_downloads.finish(ROOT,website,edition,c)
 print('Built',len(pages),'paired documents;',edition)
 return meta
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--website',type=Path);a=parser.parse_args();build(a.website)
