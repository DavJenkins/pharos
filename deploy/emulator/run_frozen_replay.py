from pathlib import Path
import os,subprocess,tarfile,hashlib,json,time,sys
base=Path('/var/lib/dataark');mount=Path('/mnt/storage')
if os.geteuid()!=0 or not Path('/etc/dataark-clean-bootstrap-test').is_file():raise SystemExit('Disposable test VM and root required')
dt=Path('/sys/firmware/devicetree/base/model');dmi=Path('/sys/class/dmi/id/product_name')
model=(dt.read_text().replace('\x00','') if dt.exists() else '')+' '+(dmi.read_text() if dmi.exists() else '')
if 'dummy-virt' not in model and 'QEMU' not in model:raise SystemExit('QEMU-only fixture')
assert not Path('/opt/dataark').exists() and not (base/'bootstrap.json').exists()
assert subprocess.check_output(['findmnt','-n','-o','SOURCE','/'],text=True).strip().startswith('/dev/vda')
assert int(Path('/sys/class/block/vdb/size').read_text())*512==16*1024**3
assert subprocess.run(['blkid','/dev/vdb'],stdout=subprocess.DEVNULL).returncode!=0
baseline={'os_release':Path('/etc/os-release').read_text(),'model':model,'clean_ark_checkout_absent':True,'bootstrap_journal_absent':True,'root_source':subprocess.check_output(['findmnt','-n','-o','SOURCE','/'],text=True).strip(),'initial_packages':subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True)}
subprocess.run(['mkfs.ext4','-q','-L','ARK-REPLAY','/dev/vdb'],check=True);mount.mkdir(exist_ok=True);subprocess.run(['mount','/dev/vdb',str(mount)],check=True);os.chown(mount,1000,1000)
with tarfile.open('/home/admin/uninterrupted-bootstrap-kit.tar.gz') as archive:
 for item in archive.getmembers():
  assert not item.issym() and not item.islnk() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  assert Path(item.name).parts[0] in ['DATA-ARK-RECOVERY','DATA-ARK-CONFIG']
 archive.extractall(mount,filter='data')
kit=mount/'DATA-ARK-RECOVERY';meta=json.loads((kit/'kit.json').read_text())
def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for name,key in [('dataark-source.tar.gz','source_sha256'),('bootstrap_stock_pi.py','bootstrap_sha256'),('pmtiles','pmtiles_sha256')]:assert digest(kit/name)==meta[key],name
assert meta['source_revision']=='5b15cc6656d623e738ca9e143ecfb4e07c6e2024' and 'test_overlay_fixes' not in meta
before={name:digest(kit/name) for name in ['dataark-source.tar.gz','bootstrap_stock_pi.py','pmtiles','site.json','kit.json']}
harness=Path('/home/admin/replay-harness.py')
with tarfile.open(kit/'dataark-source.tar.gz') as archive:harness.write_bytes(archive.extractfile('deploy/emulator/run_clean_bootstrap_test.py').read())
base.mkdir(parents=True,exist_ok=True);(base/'uninterrupted-baseline.json').write_text(json.dumps(baseline,indent=2))
report={'status':'running','source_revision':meta['source_revision'],'started_at':time.time(),'coordinator_runs':1,'manual_corrections':[],'kit_sha256_before':before,'declared_exclusions':['physical network phase','stock Pi OS marker and local-console interaction','optional content restoration'],'test_override':{'require_raspberry_pi_os':False}}
def save():(base/'uninterrupted-replay.json').write_text(json.dumps(report,indent=2))
save()
with open('/var/log/ark-uninterrupted-bootstrap.log','w') as log:
 process=subprocess.Popen(['python3',str(harness)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 while process.poll() is None:
  secret=Path('/root/clean-bootstrap-password-input');saved=Path('/root/ark-replay-verification-password')
  if secret.exists() and not saved.exists():saved.write_bytes(secret.read_bytes().splitlines()[0]);saved.chmod(0o600)
  time.sleep(1)
 report['exit_code']=process.returncode
report['kit_sha256_after']={name:digest(kit/name) for name in before};report['kit_unchanged']=report['kit_sha256_after']==before
report['status']='passed' if report['exit_code']==0 and report['kit_unchanged'] else 'failed';report['finished_at']=time.time();save();print(json.dumps(report,indent=2),flush=True)
