#!/usr/bin/env python3
"""Build the offline FCC amateur callbook from official public bulk files."""
import argparse,csv,hashlib,io,json,os,sqlite3,sys,tempfile,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/mnt/storage/civic-reference')
SOURCES=json.loads((Path(__file__).resolve().parents[1]/'deploy/reference/callsign-sources.json').read_text())
FCC=SOURCES['fcc_url']
CENSUS=SOURCES['census_url']
def acquire(path,url,limit,refresh=False):
 if path.exists() and not refresh:return
 part=path.with_suffix(path.suffix+'.part')
 try:
  with urllib.request.urlopen(url,timeout=60) as r,part.open('wb') as f:
   size=0
   while chunk:=r.read(1024**2):
    size+=len(chunk)
    if size>limit:raise ValueError('Source exceeds download cap')
    f.write(chunk)
  with zipfile.ZipFile(part) as z:
   if z.testzip():raise ValueError('Corrupt source ZIP')
  part.chmod(0o644);part.replace(path)
 finally:part.unlink(missing_ok=True)
def records(z,name):
 prefix=name[:2]+'|';pending=''
 with z.open(name) as raw:
  for line in io.TextIOWrapper(raw,encoding='latin1'):
   if line.startswith(prefix):
    if pending:yield pending.rstrip('\r\n').split('|')
    pending=line
   elif pending:pending=pending.rstrip('\r\n')+' '+line
   if len(pending)>65536:raise ValueError('Unexpected oversized FCC record')
  if pending:yield pending.rstrip('\r\n').split('|')
def build():
 archive=ROOT/'fcc-amateur-source.zip';gaz=ROOT/'zcta-2025.zip'
 target=ROOT/'callsigns.sqlite';stage=ROOT/'callsigns.sqlite.building';stage.unlink(missing_ok=True)
 db=sqlite3.connect(stage)
 try:
  db.executescript('PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; CREATE TABLE header(id INTEGER PRIMARY KEY,callsign TEXT,status TEXT,service TEXT,grant_date TEXT,expires TEXT,cancelled TEXT); CREATE TABLE entity(id INTEGER PRIMARY KEY,name TEXT,city TEXT,state TEXT,zip TEXT); CREATE TABLE zcta(zip TEXT PRIMARY KEY,lat REAL,lon REAL);')
  with zipfile.ZipFile(archive) as z:
   if sum(i.file_size for i in z.infolist())>2*1024**3:raise ValueError('Expanded FCC data exceeds cap')
   dates={i.filename:'%04d-%02d-%02d'%i.date_time[:3] for i in z.infolist()}
   count=0
   for r in records(z,'HD.dat'):
    if len(r)<10 or r[0]!='HD' or not r[1].isdigit():raise ValueError('Unexpected HD schema')
    db.execute('INSERT INTO header VALUES(?,?,?,?,?,?,?)',(int(r[1]),r[4].strip().upper(),r[5],r[6],r[7],r[8],r[9]));count+=1
    if count%100000==0:db.commit();print('Header records',count,flush=True)
   for r in records(z,'EN.dat'):
    if len(r)<19 or not r[1].isdigit():raise ValueError('Unexpected EN schema')
    if r[5]!='L':continue
    name=r[7].strip() or ' '.join(x.strip() for x in (r[8],r[9],r[10]) if x.strip())
    db.execute('INSERT OR REPLACE INTO entity VALUES(?,?,?,?,?)',(int(r[1]),name,r[16].strip(),r[17].strip(),r[18][:5]))
  with zipfile.ZipFile(gaz) as z:
   names=[n for n in z.namelist() if n.endswith('.txt')]
   if len(names)!=1:raise ValueError('Unexpected Census archive')
   with z.open(names[0]) as f:
    for r in csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'),delimiter='|'):
     r={k.strip():v.strip() for k,v in r.items()};db.execute('INSERT INTO zcta VALUES(?,?,?)',(r['GEOID'],float(r['INTPTLAT']),float(r['INTPTLONG'])))
  db.executescript('CREATE TABLE licenses AS SELECT h.*,e.name,e.city,e.state,e.zip FROM header h JOIN entity e USING(id); CREATE UNIQUE INDEX license_id ON licenses(id); CREATE INDEX license_call ON licenses(callsign); CREATE INDEX license_zip ON licenses(zip); CREATE INDEX license_state_city ON licenses(state,city); CREATE VIRTUAL TABLE names USING fts5(name,content="licenses",content_rowid="rowid"); INSERT INTO names(names) VALUES("rebuild"); DROP TABLE header; DROP TABLE entity; ANALYZE;')
  total=db.execute('SELECT count(*) FROM licenses').fetchone()[0];mapped=db.execute('SELECT count(*) FROM licenses JOIN zcta USING(zip)').fetchone()[0]
  if total<500000 or mapped<total*.5:raise ValueError('Suspiciously incomplete import')
  assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
  metadata={'retrieved_at':datetime.now(timezone.utc).isoformat(),'fcc_archive_record_dates':dates,'license_count':total,'zip_matched_count':mapped,'scope':'FCC U.S. amateur licenses, including historical statuses; no applications, GMRS, international callbooks or real-time station positions.','census_edition':SOURCES['census_edition'],'proximity':SOURCES['census_edition']+' Census ZCTA representative point matched to FCC licensee mailing ZIP; not an operating location. Unmatched ZIPs excluded from proximity results.','sources':[{'url':FCC,'file':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},{'url':CENSUS,'file':gaz.name,'sha256':hashlib.sha256(gaz.read_bytes()).hexdigest()}]}
  db.execute('CREATE TABLE metadata(json TEXT)');db.execute('INSERT INTO metadata VALUES(?)',(json.dumps(metadata),));db.commit();db.close();stage.chmod(0o644);stage.replace(target);(ROOT/'callsigns-source.json').write_text(json.dumps(metadata,indent=2)+'\n');print('Installed',total,'licenses;',mapped,'with approximate ZIP location',flush=True)
 except BaseException:
  db.close();stage.unlink(missing_ok=True);raise
def register():
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
 from app.services.manifest import load_manifest,atomic_write
 from tools.library_removal import serialize
 manifest=Path(__file__).resolve().parents[1]/'dataark.yaml';data=load_manifest(manifest)
 repo=next((r for r in data['repositories'] if r['id']=='civic-reference'),None)
 if repo is None:
  repo={'id':'civic-reference','title':'Laws, Regulations & Codes','description':'Dated civic and amateur-radio references','category':'content_sources','collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':[]};data['repositories'].append(repo)
 if not any(l['url']=='/callsigns.html' for l in repo.get('links',[])):repo.setdefault('links',[]).append({'title':'Amateur callsign search','url':'/callsigns.html'})
 for name,title,url in [('callsigns.sqlite','Offline FCC amateur callsign database',None),('fcc-amateur-source.zip','Original FCC amateur license bulk archive',FCC),('zcta-2025.zip','2025 Census ZIP-area coordinates',CENSUS)]:
  path=ROOT/name;identifier='callbook-'+name.replace('.','-');asset={'id':identifier,'repository_id':'civic-reference','category':'pdf_reference','title':title,'relative_path':'civic-reference/'+name,'service_endpoint':'/library-files/civic-reference/'+name,'expected_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'update_policy':'manual','refresh_interval':'never','source_note':'Rebuild or refresh with tools/install_callsigns.py; see callsigns-source.json for dates and source hashes.'}
  if url:asset.update(online_url=url,download_url=url)
  data['assets']=[a for a in data['assets'] if a['id']!=identifier]+[asset]
 atomic_write(manifest,serialize(data).encode())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--refresh',action='store_true');a=p.parse_args()
 if not Path('/mnt/storage').is_mount():raise SystemExit('SSD must be mounted')
 ROOT.mkdir(exist_ok=True)
 import fcntl
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  acquire(ROOT/'fcc-amateur-source.zip',FCC,400*1024**2,a.refresh);acquire(ROOT/'zcta-2025.zip',CENSUS,10*1024**2,a.refresh);build();register()
if __name__=='__main__':main()
