#!/usr/bin/env python3
"""Checkpoint public source and dependency descriptions on the content drive.
Does not image disks, copy secrets, install packages, or promise a bootable kit.
"""
import hashlib,json,os,platform,subprocess,tempfile,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 target=Path('/mnt/storage/DATA-ARK-RECOVERY')
 if not target.parent.is_mount():raise SystemExit('Content SSD must be mounted')
 target.mkdir(exist_ok=True)
 git=['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT)]
 revision=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()
 archive=target/'dataark-source.tar.gz';stage=archive.with_suffix('.tar.gz.part')
 subprocess.run(git+['archive','--format=tar.gz','--output='+str(stage),revision],check=True);stage.replace(archive)
 packages=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True)
 inventory={'recorded_at':datetime.now(timezone.utc).isoformat(),'architecture':platform.machine(),'kernel':platform.release(),'os_release':Path('/etc/os-release').read_text(),'image_origin':Path('/etc/rpi-issue').read_text() if Path('/etc/rpi-issue').exists() else None,'packages':[dict(zip(['package','version'],line.split('\t',1))) for line in packages.splitlines() if '\t' in line],'python_requirements':(ROOT/'requirements.txt').read_text(),'note':'Installed-version descriptions only. OS image, apt packages and Python wheels are not included by this command.'}
 (target/'software-baseline.json').write_text(json.dumps(inventory,indent=2)+'\n')
 (target/'recovery.yaml').write_text((ROOT/'config/recovery.yaml').read_text())
 metadata={'source_revision':revision,'source_repository':'https://github.com/DavJenkins/pharos','source_archive':archive.name,'source_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'content_restore':'implemented; complete replacement-media acceptance test remains','boot_card_restore':'experimental stock-Pi coordinator available; spare-Pi acceptance test and complete offline software cache remain','contains_credentials':False,'live_checkout_has_uncommitted_changes':subprocess.run(git+['diff','--quiet'],check=False).returncode!=0}
 (target/'readiness.json').write_text(json.dumps(metadata,indent=2)+'\n')
 (target/'README.txt').write_text('Data Ark reciprocal recovery materials\n\nSource checkpoint: '+revision+'\nThe tar.gz contains the tracked public source, not a disk image or private credentials.\nsoftware-baseline.json records versions, not cached install packages.\nrecovery.yaml describes the two-media design. readiness.json records current limits.\n\nAuthoritative content selections: /opt/dataark/config/content on the system drive.\nPortable configuration mirror: /mnt/storage/DATA-ARK-CONFIG.\nStart from supported stock Raspberry Pi OS, then use START-ARK. The coordinator is experimental and fresh-system acceptance remains.\nGuide: http://dataark/docs/20-Administration/PairedRecovery.html\n')
 (target/'index.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Data Ark recovery materials</title><h1>Data Ark recovery materials</h1><p>Public source and dependency descriptions. Boot-card recovery is not yet a tested, complete path.</p><ul>'+''.join('<li><a href="'+n+'">'+n+'</a></li>' for n in ['README.txt','dataark-source.tar.gz','software-baseline.json','recovery.yaml','readiness.json'])+'</ul><a href="/docs/20-Administration/PairedRecovery.html">Recovery guide</a></html>')
 sys.path.insert(0,str(ROOT))
 from tools.replicate_drive import kit_files
 kit_files(target.parent)
 print('Public source checkpoint saved:',revision,'at',target)
 print('No disks were imaged or changed. START-ARK setup is available; fresh-system acceptance remains.')
if __name__=='__main__':main()
