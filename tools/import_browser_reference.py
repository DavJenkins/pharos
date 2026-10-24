#!/usr/bin/env python3
"""Fixed SSH entry point for explicitly selected public PDFs; never imports private forms."""
import base64, contextlib, fcntl, hashlib, io, json, re, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
MAX=30*1024*1024
IDENTITY={
 'cdc-wrigley-en':['coping','disaster'], 'cdc-wrigley-es':['desastre','emocionales'],
 'cdc-backpack':['contact','emergency'], 'cdc-pet-kit':['pet','emergency'],
 'cdc-family-plan':['family','communication'], 'cook-good-cheap':['good','cheap'],
 'ma-form1-2025':['2025','massachusetts','form1'],
 'ma-form1-instructions-2025':['2025','massachusetts','instructions','resident'],
 'ss5':['ss5','socialsecurity'], 'usfs-before-you-go':['before','go'],
 'usfs-outdoor-safety':['outdoor','safety'], 'ma-electrical':['527','1200'],
 'ma-fire':['527','100'], 'ma-building-preamble':['780','preamble'],
 'ma-building-toc':['780','contents'], 'colorado-microhydro':['colorado','hydropower']}

def validate_pdf(data,identifier):
 if identifier not in IDENTITY:raise ValueError('Item is not approved for browser capture.')
 if not data.startswith(b'%PDF-') or len(data)>MAX:raise ValueError('Expected a PDF no larger than 30 MiB.')
 with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
  f.write(data);f.flush()
  info=subprocess.check_output(['pdfinfo',f.name],text=True,stderr=subprocess.STDOUT,timeout=30)
  if re.search(r'^Encrypted:\s+yes',info,re.M):raise ValueError('Encrypted PDFs are not accepted.')
  pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
  if not 1<=pages<=2000:raise ValueError('Unexpected page count.')
  text=subprocess.check_output(['pdftotext','-f','1','-l','3',f.name,'-'],text=True,stderr=subprocess.DEVNULL,timeout=30)
  flat=re.sub('[^a-z0-9]','',text.lower())
  if any(re.sub('[^a-z0-9]','',word) not in flat for word in IDENTITY[identifier]):
   raise ValueError('Document identity/year did not match the selected reference. Nothing installed; review the PDF.')
  if re.search(r'DRAFT AS OF|DRAFT - NOT FOR FILING',text,re.I):raise ValueError('Draft forms are not accepted.')
 return pages

def target(identifier):
 specs=[('family','family-resources'),('forms','forms'),('resilience',None)]
 for catalogue,folder in specs:
  for item in json.loads((ROOT/('deploy/reference/'+catalogue+'-catalogue.json')).read_text()):
   if item['id']==identifier:
    collection=folder or item['collection'];records_path=Path('/mnt/storage')/collection/'sources.json'
    records=json.loads(records_path.read_text());old=next((x for x in records if x.get('id')==identifier),None)
    if old is None:raise ValueError('Reference has no recorded inventory entry.')
    if old['status']=='installed' and not old.get('acquisition',{}).get('method','').startswith('user-selected browser'):
     raise ValueError('Already installed; browser capture never overwrites installed content.')
    if item.get('format','pdf')!='pdf' or identifier not in IDENTITY:raise ValueError('Only approved PDF targets are supported.')
    return catalogue,collection,item,records_path,records
 raise ValueError('Unknown reference ID.')

def install(payload):
 identifier=payload.get('id');catalogue,collection,item,records_path,records=target(identifier)
 if payload.get('source_url')!=item['url']:raise ValueError('Publisher URL does not match the current recipe. Refresh the extension target list.')
 data=base64.b64decode(payload['data'],validate=True);pages=validate_pdf(data,identifier)
 from tools import install_family_resources as family,install_forms as forms,install_resilience as resilience
 module={'family':family,'forms':forms,'resilience':resilience}[catalogue]
 class Response(io.BytesIO):
  url=item['url']
 old=next(x for x in records if x.get('id')==identifier)
 if old['status']=='installed':
  if old.get('sha256')!=hashlib.sha256(data).hexdigest():raise ValueError('Already installed with different bytes; overwrite refused.')
  record=old  # Re-publish after a lost acknowledgement/deploy failure; never rewrite the PDF.
 else:
  with contextlib.redirect_stdout(sys.stderr),patch('urllib.request.urlopen',return_value=Response(data)):
   record=module.download(item)
 if record['status']!='installed' or record['sha256']!=hashlib.sha256(data).hexdigest():raise ValueError('Installer validation failed.')
 record['acquisition']={'method':'user-selected browser download via paired SSH helper','captured_url':str(payload.get('captured_url',''))[:2048], 'checks':'PDF parser, identity/year checks, SHA-256; not a publisher digital signature'}
 records=[record if x.get('id')==identifier else x for x in records]
 module.atomic(records_path,(json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode())
 with contextlib.redirect_stdout(sys.stderr):
  if catalogue=='family':module.write_index(records)
  elif catalogue=='forms':module.index(records)
  else:module.index(collection,records)
  # Older resilience registration reconstructs its repository; preserve all preexisting artwork/order.
  from app.services.manifest import load_manifest,atomic_write
  from tools.library_removal import serialize
  before=load_manifest(ROOT/'dataark.yaml');module.register(records);after=load_manifest(ROOT/'dataark.yaml')
  for key in ['repositories','assets']:
   rank={x['id']:i for i,x in enumerate(before[key])};after[key].sort(key=lambda x:rank.get(x['id'],len(rank)))
  for repo in after['repositories']:
   old=next((x for x in before['repositories'] if x['id']==repo['id']),{})
   if 'artwork' in old:repo['artwork']=old['artwork']
  atomic_write(ROOT/'dataark.yaml',serialize(after).encode())
  gap=ROOT/'deploy/reference/content-gaps.json';report=json.loads(gap.read_text())
  row=next((x for x in report['unavailable_entries'] if x['id']==identifier),None)
  if row:
   report['unavailable_entries'].remove(row);row.update(resolution='Imported from explicitly selected browser download; PDF identity/year validated.',local_url='/library-files/'+collection+'/'+record['filename'],sha256=record['sha256'],pages=pages)
   report.setdefault('resolved_entries',[]).append(row);report['updated_at']=record['checked_at'];module.atomic(gap,(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
  for command in [[str(ROOT/'venv/bin/python'),'tools/content_profile.py','export'],[str(ROOT/'venv/bin/python'),'tools/publish_content.py'],['bash','deploy/deploy-web.sh']]:
   subprocess.run(command,cwd=ROOT,check=True,stdout=sys.stderr,stderr=sys.stderr,timeout=120)
 return {'ok':True,'message':record['title']+' installed on the Ark ('+str(pages)+' pages).','url':'/library-files/'+collection+'/'+record['filename']}

def main():
 try:
  raw=sys.stdin.buffer.read(MAX*4//3+16385)
  if len(raw)>MAX*4//3+16384:raise ValueError('Request too large.')
  payload=json.loads(raw)
  if not Path('/mnt/storage').is_mount():raise ValueError('Content drive is not mounted.')
  with Path('/var/lib/dataark/updates/browser-capture.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);answer=install(payload)
  print(json.dumps(answer))
 except Exception as e:
  print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
if __name__=='__main__':main()
