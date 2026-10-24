#!/usr/bin/env python3
"""Preserve the configured manufacturer owner documents, retaining original PDFs."""
import hashlib,json,subprocess,tempfile,urllib.request,sys,ssl
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.install_family_resources import atomic
from tools.library_removal import serialize
from app.services.manifest import load_manifest,atomic_write
import fcntl

def main():
 root=Path('/mnt/storage')
 if not root.is_mount():raise SystemExit('Content SSD must be mounted')
 context=ssl.create_default_context();context.load_verify_locations(cafile=str(ROOT/'deploy/reference/honda-intermediate.pem'))
 records=[]
 for item in json.loads((ROOT/'deploy/reference/vehicle-manuals.json').read_text()):
  req=urllib.request.Request(item['url'],headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=60,context=context) as response:data=response.read(100*1024**2+1)
  if not data.startswith(b'%PDF-') or len(data)>100*1024**2:raise ValueError('Invalid or oversized manufacturer PDF')
  with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
   f.write(data);f.flush();text=subprocess.check_output(['pdftotext','-f','1','-l','8',f.name,'-'],text=True)
   info=subprocess.check_output(['pdfinfo',f.name],text=True)
  if '2017' not in text or item['model'].lower() not in text.lower():raise ValueError('Vehicle/year verification failed: '+item['id'])
  path='vehicles/'+item['id']+'.pdf';atomic(root/path,data)
  records.append({**item,'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat(),'pdf_info':info,'scope':'Owner information and routine maintenance; not a factory workshop manual. Confirm trim, engine and equipment before following procedures. Original Honda copyright retained.'})
  print('Verified',item['title'],len(data),'bytes',flush=True)
 atomic(root/'vehicles/sources.json',(json.dumps(records,indent=2,ensure_ascii=False)+'\n').encode())
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);manifest=load_manifest(ROOT/'dataark.yaml')
  repo={'id':'vehicle-manuals','category':'content_sources','title':'Vehicle Manuals','description':'Honda owner’s manuals and quick guides for the 2017 Accord Sedan and Civic Sedan. Includes routine maintenance and roadside procedures; these are not factory workshop manuals. Confirm engine and equipment before use.','artwork':{'path':'app/static/assets/icons/Repair.png','alt':'Vehicle maintenance icon'},'update_policy':'manual','refresh_interval':'never','links':[]}
  manifest['repositories']=[r for r in manifest['repositories'] if r['id']!=repo['id']]+[repo]
  for r in records:
   asset={'id':r['id'],'repository_id':repo['id'],'category':'pdf_reference','title':r['title'],'relative_path':r['path'],'service_endpoint':'/library-files/'+r['path'],'download_url':r['url'],'online_url':r['url'],'expected_hash':r['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':r['scope']+' Retrieved '+r['retrieved_at']}
   manifest['assets']=[a for a in manifest['assets'] if a['id']!=asset['id']]+[asset]
  atomic_write(ROOT/'dataark.yaml',serialize(manifest).encode())
if __name__=='__main__':main()
