#!/usr/bin/env python3
"""Stage and verify the 50-state map on the Ark. Never replaces the published map."""
from pathlib import Path
import fcntl,hashlib,json,os,shutil,subprocess,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
STATE=Path('/var/lib/dataark/maps/usa-expansion.json')
def save(**fields):
    fields['updated_at']=datetime.now(timezone.utc).isoformat();p=STATE.with_suffix('.json.tmp');p.write_text(json.dumps(fields,indent=2)+'\n');p.replace(STATE)
def main():
    config=json.loads((ROOT/'deploy/reference/osm-usa.json').read_text())
    if 'memory' not in Path('/sys/fs/cgroup/cgroup.controllers').read_text().split():raise SystemExit('Memory controller is disabled. Apply enable_memory_limits.py, reboot, and verify before extraction.')
    target=Path('/mnt/storage/maps/osm/usa.staging.pmtiles')
    if not Path('/mnt/storage').is_mount():raise SystemExit('Content SSD is not mounted.')
    if shutil.disk_usage(target.parent).free<config['reserve_gib']*1024**3:raise SystemExit('Not enough free staging space.')
    if target.exists():raise SystemExit('Staging file exists; inspect it before retrying. It is not a published map.')
    with Path('/var/lib/dataark/maps/worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        started=time.time()
        try:
            save(state='downloading',source=config['source'])
            subprocess.run(['/usr/local/bin/pmtiles','extract',config['source'],str(target),'--region='+str(ROOT/config['region']),'--maxzoom='+str(config['maxzoom']),'--download-threads=2'],check=True)
            save(state='verifying',bytes=target.stat().st_size)
            subprocess.run(['/usr/local/bin/pmtiles','verify',str(target)],check=True)
            digest=hashlib.sha256()
            with target.open('rb') as stream:
                for chunk in iter(lambda:stream.read(4*1024**2),b''):digest.update(chunk)
            header=json.loads(subprocess.check_output(['/usr/local/bin/pmtiles','show',str(target),'--header-json'],text=True))
            save(state='verified',file=str(target),bytes=target.stat().st_size,sha256=digest.hexdigest(),header=header,seconds=round(time.time()-started))
        except Exception as error:save(state='failed',error=str(error));raise
if __name__=='__main__':main()
