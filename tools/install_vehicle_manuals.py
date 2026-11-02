#!/usr/bin/env python3
"""Acquire configured vehicle PDFs or refresh their explicit source metadata."""
import argparse,fcntl,hashlib,json,subprocess,tempfile,urllib.request,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.install_family_resources import atomic
from tools.library_removal import serialize
from tools.vehicle_catalogue import load,validate_document,source_note,render_index
from tools.source_tls import context
from app.services.manifest import load_manifest,atomic_write

MAX_BYTES=100*1024**2

def download(item):
 request=urllib.request.Request(item['url'],headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(request,timeout=60,context=context(item['url'],ROOT)) as response:
  return response.read(MAX_BYTES+1)

def pdf_metadata(data):
 with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
  f.write(data);f.flush()
  text=subprocess.check_output(['pdftotext','-f','1','-l','8',f.name,'-'],text=True)
  info=subprocess.check_output(['pdfinfo',f.name],text=True)
 return text,info

def collect(catalogue,root,metadata_only=False,fetch=download):
 previous_path=root/'vehicles/sources.json'
 previous={r['id']:r for r in json.loads(previous_path.read_text())} if previous_path.is_file() else {}
 records=[]
 for item in catalogue['documents']:
  relative='vehicles/'+item['id']+'.pdf';target=root/relative
  if target.is_symlink():raise ValueError('Vehicle PDF cannot be a symlink')
  old=previous.get(item['id'],{})
  if metadata_only:
   if not target.is_file() or target.stat().st_size>MAX_BYTES:raise ValueError('Verified existing PDF required: '+item['id'])
   data=target.read_bytes()
   expected=item.get('sha256') or old.get('sha256')
   if not expected or hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Existing PDF checksum mismatch: '+item['id'])
  else:data=fetch(item)
  if not data.startswith(b'%PDF-') or len(data)>MAX_BYTES:raise ValueError('Invalid or oversized manufacturer PDF')
  digest=hashlib.sha256(data).hexdigest()
  if item.get('sha256') and digest!=item['sha256']:raise ValueError('Configured PDF checksum mismatch: '+item['id'])
  if item.get('bytes') and len(data)!=item['bytes']:raise ValueError('Configured PDF size mismatch: '+item['id'])
  text,info=pdf_metadata(data);validate_document(item,text)
  if not metadata_only:atomic(target,data)
  record={**item,'path':relative,'bytes':len(data),'sha256':digest,'retrieved_at':old.get('retrieved_at') if metadata_only else datetime.now(timezone.utc).isoformat(),'pdf_info':info}
  if metadata_only:record['metadata_updated_at']=datetime.now(timezone.utc).isoformat()
  records.append(record)
 return records

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--metadata-only',action='store_true',help='Verify existing PDFs and refresh notices without downloading or rewriting documents');args=parser.parse_args()
 root=Path('/mnt/storage')
 if not root.is_mount():raise SystemExit('Content drive must be mounted')
 catalogue=load(ROOT/'deploy/reference/vehicle-manuals.json')
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  records=collect(catalogue,root,args.metadata_only)
  atomic(root/'vehicles/sources.json',(json.dumps(records,indent=2,ensure_ascii=False)+'\n').encode())
  from app.services.documentation_theme import masthead,footer,stylesheet_url
  page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vehicle documents and notices</title><link rel="stylesheet" href="'+stylesheet_url()+'"></head><body class="ark-documentation"><div class="documentation-shell">'+masthead('SOURCE NOTICES','help')+'<main class="docs-paper handbook-paper">'+render_index(records)+'</main>'+footer()+'</div></body></html>'
  atomic(root/'vehicles/index.html',page.encode())
  manifest=load_manifest(ROOT/'dataark.yaml');repo=catalogue['repository']
  existing=next((r for r in manifest['repositories'] if r['id']==repo['id']),None)
  if existing:existing.update(description=repo['description'],links=repo.get('links',[]))
  else:manifest['repositories'].append(repo)
  for record in records:
   asset=next((a for a in manifest['assets'] if a['id']==record['id']),None)
   metadata={'id':record['id'],'repository_id':repo['id'],'category':'pdf_reference','title':record['title'],'relative_path':record['path'],'service_endpoint':'/library-files/'+record['path'],'download_url':record['url'],'online_url':record['url'],'expected_hash':record['sha256'],'source_note':source_note(record),'source_metadata':{key:record[key] for key in ('publisher','document_kind','scope','applicability','rights_notice')}}
   if asset:asset.update(metadata)
   else:manifest['assets'].append({**metadata,'update_policy':'manual','refresh_interval':'never'})
  atomic_write(ROOT/'dataark.yaml',serialize(manifest).encode())
  print('Verified source metadata for',len(records),'configured vehicle documents; original PDFs '+('unchanged' if args.metadata_only else 'preserved'))
if __name__=='__main__':main()
