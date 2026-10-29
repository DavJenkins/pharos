#!/usr/bin/python3
"""Prepare an already mounted drive as a Data Ark installer, optionally with content.
No formatting, deletion or credentials. Default is a preview.
"""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/mnt/storage')
PUBLIC_DIRS=[item['path'] for item in json.loads((ROOT/'config/clone-policy.json').read_text())['public_directories']]
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
 from tools.clone_drive import inspect_target
 result=inspect_target(target)
 if not result['eligible']:raise ValueError('; '.join(result['reasons']))
 if bool(result.get('resume'))!=resume:raise ValueError('Use --resume only for the matching incomplete clone.')
 return target.resolve()

def kit_files(target, profile=None, revision=None, platform_profile=None):
 git=['git','-c','safe.directory='+str(ROOT),'-c','core.filemode=false','-C',str(ROOT)]
 current=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()
 if revision and revision!=current:raise ValueError('Use the approved source checkpoint when preparing its installer kit.')
 executable_paths=[':(glob)app/**/*.py',':(glob)tools/**/*.py',':(glob)deploy/**/*.py','deploy/platforms','config/stock-pi.json']
 if subprocess.run(git+['diff','--quiet','HEAD','--']+executable_paths).returncode:raise ValueError('Commit installer/platform code changes before preparing a kit; private content selections need not be committed.')
 untracked=subprocess.check_output(git+['ls-files','--others','--exclude-standard','--','app','tools','deploy'],text=True).splitlines()
 if any(name.endswith('.py') or name.startswith('deploy/platforms/') for name in untracked):raise ValueError('Untracked installer code/profile files must be reviewed and committed before preparing a kit.')
 # Mirror the saved desired profile; never recapture an empty destination as intent.
 from tools.content_profile import mirror,read
 profile=Path(profile) if profile else ROOT/'config/content/content.yaml';mirror(read(profile),profile.parent,target/'DATA-ARK-CONFIG')
 kit=target/'DATA-ARK-RECOVERY';kit.mkdir(parents=True,exist_ok=True)
 revision=revision or subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 from tools.build_bootstrap_release import archive_bytes,inspect_config
 import io,tarfile,yaml
 raw=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'archive','--format=tar',revision])
 with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
  files={m.name:(archive.extractfile(m).read(),m.mode) for m in archive.getmembers() if m.isfile()}
 public=read(profile.parent/read(profile)['manifest']);inspect_config(public)
 files['dataark.yaml']=(yaml.safe_dump(public,sort_keys=False,allow_unicode=True).encode(),0o644)
 (kit/'dataark-source.tar.gz').write_bytes(archive_bytes(files))
 shutil.copyfile(ROOT/'deploy/bootstrap_stock_pi.py',kit/'bootstrap_stock_pi.py')
 site=json.loads((ROOT/'config/stock-pi.json').read_text())
 if site.get('kiwix_image')=='ghcr.io/kiwix/kiwix-serve@sha256:7431be257ac0b0b6f14633ef088774f6d5122246940b594b3017a70169058b08':
  site['kiwix_image']=json.loads((ROOT/'config/stock-pi.json').read_text())['kiwix_image']
 for required in ['ethtool','docker-cli','ntfs-3g']:
  if required not in site['packages']:site['packages'].append(required)
 (kit/'site.json').write_text(json.dumps(site,indent=2)+'\n')
 from deploy import bootstrap_platform as platforms
 from tools.platform_tools import pmtiles as platform_tool
 if platform_profile:site=platforms.configure(site,platform_profile)
 else:
  installed=ROOT/'config/installed-site.json'
  name=json.loads(installed.read_text()).get('platform_profile',platforms.DEFAULT) if installed.is_file() else platforms.DEFAULT
  site=platforms.configure(site,name)
 (kit/'site.json').write_text(json.dumps(site,indent=2)+'\n')
 spec=platforms.selected(site)
 pmtiles=platform_tool(spec,ROOT/'output/platform-tools')
 platform_files={}
 for source,name in [(ROOT/'deploy/bootstrap_platform.py','bootstrap_platform.py')]+[(p,'platforms/'+p.name) for p in sorted((ROOT/'deploy/platforms').glob('*.json'))]:
  dest=kit/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);platform_files[name]=sha(dest)
 shutil.copyfile(pmtiles,kit/'pmtiles');(kit/'pmtiles').chmod(0o755)
 shutil.copyfile(ROOT/'deploy/reference/pmtiles-LICENSE.txt',kit/'PMTILES-LICENSE.txt')
 (kit/'PMTILES-NOTICE.txt').write_text('Protomaps go-pmtiles CLI '+spec['pmtiles']['version']+', BSD-3-Clause; official source https://github.com/protomaps/go-pmtiles . Processor: '+spec['baseline']['architecture']+'. Official archive SHA-256: '+spec['pmtiles']['archive_sha256']+'. Binary checksum recorded in kit.json.\n')
 metadata={'schema':1,'source_revision':revision,'source_sha256':sha(kit/'dataark-source.tar.gz'),'bootstrap_sha256':sha(kit/'bootstrap_stock_pi.py'),'pmtiles_sha256':sha(kit/'pmtiles'),'status':'experimental_platform_installer_acceptance_pending','credentials_included':False,'device_identity_included':False,'public_manifest_only':True,'platform_profile':spec['id'],'architecture':spec['baseline']['architecture'],'platform_files':platform_files}
 (kit/'kit.json').write_text(json.dumps(metadata,indent=2)+'\n');(target/'START-ARK.sh').write_text(START);(target/'START-ARK.sh').chmod(0o755)
 text='''Data Ark installation drive

Selected platform: PLATFORM. Debian 13 (Trixie),
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
keeps the restoration choices without starting optional content downloads. It preserves saved selections when files are absent. Interrupted
software phases can be resumed using the same command and site settings.

This coordinator has unit/preflight tests but has not passed a fresh spare-system
installation test. Follow the bundled docs/30-Developer/StockPiSetup.md in the
source archive for the acceptance checklist and current boundaries.

To prepare another drive after installation:
  cd /opt/dataark
  sudo venv/bin/python tools/replicate_drive.py --target /path/to/mounted/drive --mode config
Review the preview and run its exact command including --accept-plan and --apply.
Use --mode fit for whole collections that fit, or populated for all public content. No private household
backups, credentials, host keys or Linux login files are copied.
'''
 text=text.replace('PLATFORM',spec['label'])
 text=text.replace('Apply only on the supported target:\n  sudo bash START-ARK.sh --apply', 'Review the discovery plan and use the exact apply command it prints, including --accept-plan.')
 if spec['network_mode']=='lan':text=text.replace('It will turn wlan0 into an open\nDataArk hotspot;', 'Existing LAN connections are preserved; no hotspot is created;')
 (target/'START-ARK.txt').write_text(text)
 (target/'START-ARK.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Set up a Data Ark</title><h1>Set up a Data Ark</h1><pre>'+text.replace('&','&amp;').replace('<','&lt;')+'</pre></html>')
 return metadata
def copy_public_content(target,paths):
 subprocess.run(['rsync','-rt','--no-links','--no-specials','--no-devices','--partial','--append-verify','--info=progress2','--no-owner','--no-group','--relative']+['./'+n for n in paths]+[str(target)+'/'],check=True,cwd=SOURCE)

def main():
 import sys
 sys.path.insert(0,str(ROOT))
 from tools.clone_drive import main as clone_main
 clone_main()
if __name__=='__main__':main()
