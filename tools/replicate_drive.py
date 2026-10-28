#!/usr/bin/python3
"""Prepare an already mounted drive as a Data Ark installer, optionally with content.
No formatting, deletion or credentials. Default is a preview.
"""
import argparse,fcntl,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/mnt/storage')
PUBLIC_DIRS=['communication','vehicles','preparedness','forms','family-resources','resilience','civic-reference','radio-study','maps','kiwix-viewer']
START='''#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$HERE/DATA-ARK-RECOVERY/bootstrap_stock_pi.py" --kit "$HERE/DATA-ARK-RECOVERY" "$@"
'''
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def payload_paths():
 import yaml
 c=yaml.safe_load((ROOT/'config/content/content.yaml').read_text());paths=[p for p in PUBLIC_DIRS if (SOURCE/p).is_dir() and not (SOURCE/p).is_symlink()]
 paths += [a['path'] for a in c['archives'] if a.get('enabled') and (SOURCE/a['path']).is_file()]
 paths += [p for p in ['START-HERE.html','README-DATA-ARK.txt','BROWSE.html','DATA-ARK-CATALOG.json'] if (SOURCE/p).is_file()]
 return paths
def safe_target(target,resume=False):
 target=target.resolve()
 if target==SOURCE.resolve() or target==Path('/') or not target.is_mount():raise ValueError('Choose a separate, already mounted replacement drive.')
 if target.stat().st_dev==SOURCE.stat().st_dev or target.stat().st_dev==Path('/').stat().st_dev:raise ValueError('Target must not share the live content or system filesystem.')
 if any((target/n).exists() for n in PUBLIC_DIRS+['DATA-ARK-CONFIG','DATA-ARK-RECOVERY','START-ARK.sh']):
  meta=target/'DATA-ARK-RECOVERY/kit.json'
  if not resume or not meta.is_file():raise ValueError('Target contains reserved Ark paths. Use --resume only for this tool’s interrupted preparation.')
  saved=json.loads(meta.read_text())
  if saved.get('preparation_state')!='copying' or saved.get('profile_sha256')!=sha(ROOT/'config/content/content.yaml'):raise ValueError('Not a matching interrupted preparation; refusing to overwrite.')
 return target
def kit_files(target):
 # Mirror the saved desired profile; never recapture an empty destination as intent.
 from tools.content_profile import mirror,read
 profile=ROOT/'config/content/content.yaml';mirror(read(profile),profile.parent,target/'DATA-ARK-CONFIG')
 kit=target/'DATA-ARK-RECOVERY';kit.mkdir(parents=True,exist_ok=True)
 revision=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 subprocess.run(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'archive','--format=tar.gz','--output='+str(kit/'dataark-source.tar.gz'),revision],check=True)
 shutil.copyfile(ROOT/'deploy/bootstrap_stock_pi.py',kit/'bootstrap_stock_pi.py');shutil.copyfile(ROOT/'config/installed-site.json' if (ROOT/'config/installed-site.json').is_file() else ROOT/'config/stock-pi.json',kit/'site.json')
 preference=Path('/etc/dataark/wifi-roles.json')
 if preference.is_file():shutil.copyfile(preference,kit/'wifi-roles.json')
 site=json.loads((kit/'site.json').read_text())
 if 'ethtool' not in site['packages']:site['packages'].append('ethtool')
 (kit/'site.json').write_text(json.dumps(site,indent=2)+'\n')
 pmtiles=Path('/usr/local/bin/pmtiles')
 if not pmtiles.is_file():raise RuntimeError('Install the documented official ARM64 PMTiles CLI before preparing a replication kit.')
 shutil.copyfile(pmtiles,kit/'pmtiles');(kit/'pmtiles').chmod(0o755)
 shutil.copyfile(ROOT/'deploy/reference/pmtiles-LICENSE.txt',kit/'PMTILES-LICENSE.txt')
 (kit/'PMTILES-NOTICE.txt').write_text('Protomaps go-pmtiles CLI 1.31.2, BSD-3-Clause; official source https://github.com/protomaps/go-pmtiles . Original release tarball SHA-256: f8bd47e7ea866863489cad588fbaf2f31f42e5821f7a03f009b3769f05801cb1. Binary checksum recorded in kit.json.\n')
 metadata={'schema':1,'source_revision':revision,'source_sha256':sha(kit/'dataark-source.tar.gz'),'bootstrap_sha256':sha(kit/'bootstrap_stock_pi.py'),'pmtiles_sha256':sha(kit/'pmtiles'),'status':'experimental_stock_pi_installer_spare_system_acceptance_pending','credentials_included':False}
 (kit/'kit.json').write_text(json.dumps(metadata,indent=2)+'\n');(target/'START-ARK.sh').write_text(START);(target/'START-ARK.sh').chmod(0o755)
 text='''Data Ark installation drive

Supported starting point: Raspberry Pi OS 64-bit based on Debian 13 (Trixie),
with primary account admin (UID 1000). Use a local terminal and Ethernet or a
second Wi-Fi adapter for upstream internet. This installer needs internet for
OS/Python/container software; this is not a complete offline software kit.

Read/edit DATA-ARK-RECOVERY/site.json for SSID, country and content choices.
Preview from this drive's directory:
  sudo bash START-ARK.sh
Apply only on the supported target:
  sudo bash START-ARK.sh --apply
Setup shows its plan and asks for INSTALL before making changes. It asks for
a separate administration password privately. It will turn wlan0 into an open
DataArk hotspot; existing Ark installations are refused. It never formats disks.

A populated drive reuses existing library files. A configuration-only drive
downloads/regenerates missing selections; this may take hundreds of GB and a
long time. It preserves saved selections when files are absent. Interrupted
software phases can be resumed using the same command and site settings.

This coordinator has unit/preflight tests but has not passed a fresh spare-Pi
installation test. Follow the bundled docs/30-Developer/StockPiSetup.md in the
source archive for the acceptance checklist and current boundaries.

To prepare another drive after installation:
  cd /opt/dataark
  sudo venv/bin/python tools/replicate_drive.py --target /path/to/mounted/drive --mode config --apply
Use --mode populated to include public library content. No private household
backups, credentials, host keys or Linux login files are copied.
'''
 (target/'START-ARK.txt').write_text(text)
 (target/'START-ARK.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Set up a Data Ark</title><h1>Set up a Data Ark</h1><pre>'+text.replace('&','&amp;').replace('<','&lt;')+'</pre></html>')
 return metadata
def copy_public_content(target,paths):
 subprocess.run(['rsync','-rt','--no-links','--no-specials','--no-devices','--partial','--append-verify','--info=progress2','--no-owner','--no-group','--relative']+['./'+n for n in paths]+[str(target)+'/'],check=True,cwd=SOURCE)

def main():
 import sys
 sys.path.insert(0,str(ROOT))
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--mode',choices=['config','populated'],default='config');p.add_argument('--apply',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 target=safe_target(a.target,a.resume);paths=payload_paths() if a.mode=='populated' else [];size=0
 for name in paths:
  f=SOURCE/name
  for source_file in ([p for p in f.rglob('*') if p.is_file() and not p.is_symlink()] if f.is_dir() else [f]):
   destination=target/source_file.relative_to(SOURCE)
   if destination.is_symlink():raise ValueError('Unexpected destination symlink')
   size+=max(0,source_file.stat().st_size-(destination.stat().st_size if a.resume and destination.is_file() else 0))
 print('Target:',target,'Mode:',a.mode,'Public content bytes:',size,'\nNo formatting, deletion or private configuration copying.')
 if not a.apply:print('Preview only; add --apply to prepare this drive.');return
 if os.geteuid()!=0:raise SystemExit('Run explicit drive preparation with sudo.')
 if shutil.disk_usage(target).free<size+2*1024**3:raise SystemExit('Insufficient free space for requested content plus reserve.')
 locks=[]
 for name in ['/var/lib/dataark/updates/worker.lock','/var/lib/dataark/maps/worker.lock']:
  lock=Path(name).open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
 if a.resume:
  metadata=json.loads((target/'DATA-ARK-RECOVERY/kit.json').read_text())
  if metadata.get('preparation_mode')!=a.mode:raise SystemExit('Use the same mode as the interrupted preparation.')
 else:metadata=kit_files(target)
 metadata.update(preparation_state='copying',preparation_mode=a.mode,profile_sha256=sha(ROOT/'config/content/content.yaml'))
 (target/'DATA-ARK-RECOVERY/kit.json').write_text(json.dumps(metadata,indent=2)+'\n')
 shutil.chown(target,user='admin',group='admin')
 if paths:copy_public_content(target,paths)
 for name in PUBLIC_DIRS+['DATA-ARK-CONFIG','DATA-ARK-RECOVERY']:
  directory=target/name
  if directory.is_dir():
   for path in [directory]+list(directory.rglob('*')):
    if not path.is_symlink():shutil.chown(path,user='admin',group='admin')
 metadata['preparation_state']='ready';(target/'DATA-ARK-RECOVERY/kit.json').write_text(json.dumps(metadata,indent=2)+'\n')
 print('Prepared:',target/'START-ARK.txt','\nSafely unmount the drive, connect it to a supported Pi and follow START-ARK.')
if __name__=='__main__':main()
