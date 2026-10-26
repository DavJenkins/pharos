#!/usr/bin/env python3
"""Extract, verify and publish the selected Caribbean map; retain U.S. maps."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,os,re,shutil,subprocess,threading,time
import yaml
ROOT=Path(__file__).resolve().parents[1]
STATUS=Path('/var/lib/dataark/updates/status.json')
LOG=Path('/var/lib/dataark/maps/caribbean-extract.log')
CONFIG=ROOT/'deploy/reference/osm-caribbean.json'
DONE=threading.Event()
phase='downloading'
def status():
 percent=0
 try:
  with LOG.open('rb') as f:
   f.seek(0,2);size=f.tell();f.seek(max(0,size-8192));values=re.findall(r'fetching chunks\s+(\d+)%',f.read().decode(errors='replace'))
  if values:percent=int(values[-1])
 except OSError:pass
 v={'state':phase,'asset':'Caribbean offline map','updated':datetime.now(timezone.utc).isoformat(timespec='seconds')}
 if phase=='downloading':v['percent']=percent
 tmp=STATUS.with_suffix('.caribbean.tmp');tmp.write_text(json.dumps(v)+'\n');tmp.replace(STATUS)
def heartbeat():
 while not DONE.wait(30):status()
def main():
 global phase
 cfg=json.loads(CONFIG.read_text());target=Path('/mnt/storage')/cfg['path'];stage=target.with_name('caribbean.staging.pmtiles')
 if not Path('/mnt/storage').is_mount() or shutil.disk_usage(target.parent).free < cfg['reserve_gib']*1024**3:raise RuntimeError('Mounted content drive and 40 GiB reserve are required')
 if target.exists() or stage.exists():raise RuntimeError('Map or staging file exists; inspect before replacing')
 with Path('/var/lib/dataark/maps/worker.lock').open('a') as lock,Path('/var/lib/dataark/updates/worker.lock').open('a') as updates:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(updates,fcntl.LOCK_EX|fcntl.LOCK_NB)
  status();thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
  try:
   with LOG.open('w') as log:subprocess.run(['/usr/local/bin/pmtiles','extract','http://127.0.0.1:8097/source.pmtiles',str(stage),'--bbox='+','.join(map(str,cfg['bbox'])),'--maxzoom=15','--download-threads=2'],stdout=log,stderr=subprocess.STDOUT,check=True)
   phase='verifying';status();subprocess.run(['/usr/local/bin/pmtiles','verify',str(stage)],check=True)
   digest=hashlib.sha256()
   with stage.open('rb') as f:
    for part in iter(lambda:f.read(4*1024**2),b''):digest.update(part)
   header=json.loads(subprocess.check_output(['/usr/local/bin/pmtiles','show',str(stage),'--header-json'],text=True))
   if header['maxzoom']!=15:raise RuntimeError('Unexpected map detail level')
   phase='activating';status();size=stage.stat().st_size;stage.replace(target)
   cfg.update(bytes=size,sha256=digest.hexdigest(),configuration_state='verified and published');CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
   target.with_name('caribbean-source.json').write_text(json.dumps(cfg,indent=2)+'\n')
   p=ROOT/'dataark.yaml';m=yaml.safe_load(p.read_text())
   if not any(a['id']=='osm-caribbean' for a in m['assets']):m['assets'].append({'id':'osm-caribbean','repository_id':'openstreetmap','category':'reference','title':'Caribbean islands offline street map (October 22, 2026)','relative_path':cfg['path'],'service_endpoint':'/maps.html?collection=caribbean','update_policy':'manual','refresh_interval':'never','online_url':'https://docs.protomaps.com/basemaps/downloads','expected_hash':cfg['sha256'],'version_pin':None,'source_note':cfg['scope']})
   for repo in m['repositories']:
    if repo['id']=='openstreetmap':repo['description']='Offline street maps for all 50 U.S. states and Caribbean islands, including USVI and Sint Maarten/Saint-Martin. Local pan and zoom; no routing.'
   p.write_text(yaml.safe_dump(m,sort_keys=False,allow_unicode=True))
   subprocess.run(['/usr/bin/python3','tools/content_profile.py','export'],cwd=ROOT,check=True)
   subprocess.run([str(ROOT/'venv/bin/python'),'-m','unittest','tests.test_manifest','tests.test_maps','tests.test_content_profile'],cwd=ROOT,check=True)
   subprocess.run(['bash','deploy/deploy-web.sh'],cwd=ROOT,check=True)
   from urllib.request import Request,urlopen
   with urlopen(Request('http://127.0.0.1/library-files/'+cfg['path'],headers={'Range':'bytes=0-126'}),timeout=20) as response:
    if response.status!=206 or response.read(128)[:8]!=b'PMTiles\x03':raise RuntimeError('Published archive endpoint failed')
   phase='idle';status();print('Published Caribbean archive:',size,'bytes SHA256',cfg['sha256'],flush=True)
  except Exception:
   phase='error';status();raise
  finally:DONE.set();thread.join(timeout=2)
if __name__=='__main__':main()
