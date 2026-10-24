#!/usr/bin/env python3
"""Install pinned, licensed NCVEC question-pool transcription and diagrams."""
import hashlib,json,re,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
COMMIT='6122699c9541f26d88298db379b5e252885c42a2'
BASE='https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/'+COMMIT+'/'
ROOT=Path('/mnt/storage/radio-study')
POOLS=[('technician','2026-2030','2026-07-01','2030-06-30',409,35,26,['t-1.png','t-2.png','t-3.png']),('general','2023-2027','2023-07-01','2027-06-30',423,35,26,['g7-1.png']),('extra','2024-2028','2024-07-01','2028-06-30',599,50,37,['e5-1.png','e6-1.png','e6-2.png','e6-3.png','e7-1.png','e7-2.png','e7-3.png','e9-1.png','e9-2.png','e9-3.png'])]
WITHDRAWN=set('G1A04 G1C08 G1C09 G1C10 G1E09 G6B09 G8C01 G9C06 G9D13 E2A13 E4D05 E6D07 E9E10'.split())
def get(path):
 with urllib.request.urlopen(BASE+path,timeout=30) as r:data=r.read(8*1024**2+1)
 if len(data)>8*1024**2:raise ValueError('Source exceeds cap')
 return data
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);stage=path.with_suffix(path.suffix+'.part');stage.write_bytes(data);stage.chmod(0o644);stage.replace(path)
def main():
 if not Path('/mnt/storage').is_mount():raise SystemExit('SSD must be mounted')
 import fcntl
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);meta={'source':'NCVEC public-domain pools; machine-readable transcription and figures by russolsen/ham_radio_question_pool (Apache-2.0)','mirror_commit':COMMIT,'retrieved_at':datetime.now(timezone.utc).isoformat(),'errata_check':'Technician February 19, 2026 wording verified; General/Extra withdrawn questions checked against ARRL withdrawn list October 23, 2026. No official teaching explanations are supplied.','sources':['https://www.ncvec.org/index.php/2026-2030-technician-question-pool','https://www.ncvec.org/index.php/2023-2027-general-question-pool-release','https://www.ncvec.org/index.php/2024-2028-extra-class-question-pool-release','https://www.arrl.org/withdrawn-questions'],'pools':[],'files':[]}
  files={'LICENSE.txt':get('LICENSE.txt')}
  for key,edition,start,end,count,exam,passing,figures in POOLS:
   directory=key+'-'+edition;raw=get(directory+'/'+directory+'.json');rows=json.loads(raw)
   assert len(rows)==count and len({r['id'] for r in rows})==count,'Pool count/duplicate mismatch'
   assert not WITHDRAWN.intersection(r['id'] for r in rows),'Withdrawn questions present'
   for r in rows:
    assert re.fullmatch('[TGE][0-9][A-Z][0-9]{2}',r['id']) and len(r['answers'])==4
    assert isinstance(r['correct'],int) and 0<=r['correct']<4 and r['correct_letter']=='ABCD'[r['correct']]
    assert r.get('figure','') in ['']+figures,'Unknown figure'
   if key=='technician':
    expected={'T1C01':'For which classes of amateur radio licenses does the FCC currently issue new licenses?','T5A05':'A difference in which of the following causes electron flow?','T7A09':'What is the function of the switch which selects either SSB or CW-FM on some VHF power amplifiers?','T0A10':'What hazard exists when rapidly charging or discharging an unprotected battery?'}
    for id,text in expected.items():assert next(r['question'] for r in rows if r['id']==id)==text
   assert len({r['id'][:3] for r in rows})==exam,'Exam group coverage mismatch'
   # Original mirror data remains unchanged; provenance is in the separate manifest.
   files[directory+'/'+directory+'.json']=raw;files[directory+'/'+directory+'.txt']=get(directory+'/'+directory+'.txt')
   for figure in figures:
    data=get(directory+'/'+figure);assert data.startswith(b'\x89PNG\r\n\x1a\n');files[directory+'/'+figure]=data
   meta['pools'].append({'id':key,'title':'Amateur Extra' if key=='extra' else key.title(),'edition':edition,'valid_from':start,'valid_through':end,'count':count,'exam_questions':exam,'passing':passing,'data':directory+'/'+directory+'.json','directory':directory,'figures':figures})
  for name,data in files.items():atomic(ROOT/name,data);meta['files'].append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'url':BASE+name if name=='LICENSE.txt' else BASE+name})
  atomic(ROOT/'source.json',(json.dumps(meta,indent=2)+'\n').encode())
  atomic(ROOT/'index.html',b'<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/radio-study.html"><title>Radio study</title></head><body><a href="/radio-study.html">Open the offline amateur-radio question drill</a> or <a href="source.json">read source and edition records</a>.</body></html>')
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from app.services.manifest import load_manifest,atomic_write
  from tools.library_removal import serialize
  path=Path(__file__).resolve().parents[1]/'dataark.yaml';m=load_manifest(path);repo={'id':'radio-study','title':'Amateur Radio Exam Practice','description':'Technician, General and Amateur Extra question pools, diagrams and offline drills.','category':'content_sources','collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':[{'title':'Practice radio exam questions','url':'/radio-study.html'},{'title':'Pool sources and editions','url':'/library-files/radio-study/source.json'}]};m['repositories']=[r for r in m['repositories'] if r['id']!='radio-study']+[repo]
  for p in meta['pools']:
   for suffix in ['json','txt']:
    name=p['directory']+'/'+p['directory']+'.'+suffix;data=files[name];id='radio-'+p['id']+'-'+suffix;a={'id':id,'repository_id':'radio-study','category':'pdf_reference','title':p['title']+' '+p['edition']+' question pool ('+suffix.upper()+')','relative_path':'radio-study/'+name,'service_endpoint':'/library-files/radio-study/'+name,'expected_hash':hashlib.sha256(data).hexdigest(),'update_policy':'manual','refresh_interval':'never','online_url':BASE+name,'download_url':BASE+name,'source_note':'Pinned licensed transcription; reinstall using tools/install_radio_study.py. Figures and source record accompany collection.'};m['assets']=[x for x in m['assets'] if x['id']!=id]+[a]
  atomic_write(path,serialize(m).encode())
  from tools.publish_content import publish
  publish(Path('/mnt/storage'));print('Installed 1431 questions and 14 diagrams',flush=True)
if __name__=='__main__':main()
