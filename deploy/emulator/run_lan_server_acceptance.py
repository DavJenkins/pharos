"""Acceptance entry point for a newly created, marked QEMU VM only."""
from pathlib import Path
import os,sys,tarfile,subprocess,json,hashlib,time,pty,select,secrets
assert os.geteuid()==0 and Path('/etc/dataark-lan-acceptance-test').is_file()
model=' '.join(p.read_text().replace('\0','') for p in [Path('/sys/firmware/devicetree/base/model'),Path('/sys/class/dmi/id/product_name')] if p.exists())
assert 'dummy-virt' in model or 'QEMU' in model
assert not Path('/opt/dataark').exists()
assert subprocess.check_output(['findmnt','-n','-o','SOURCE','/'],text=True).strip().startswith('/dev/vda')
assert int(Path('/sys/class/block/vdb/size').read_text())*512==16*1024**3
assert subprocess.run(['blkid','/dev/vdb'],stdout=subprocess.DEVNULL).returncode!=0
state=Path('/var/lib/dataark-lan-acceptance');state.mkdir(mode=0o700)
def network_snapshot():
 paths=[Path('/etc/hostname'),Path('/etc/network/interfaces')]
 for directory in ['/etc/systemd/network','/etc/NetworkManager/system-connections','/etc/netplan']:
  folder=Path(directory)
  if folder.exists():paths+=list(folder.rglob('*'))
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file() and not p.is_symlink()}
before=network_snapshot();(state/'network-before.json').write_text(json.dumps(before,indent=2))
subprocess.run(['mkfs.ext4','-q','-L','ARK-LAN-TEST','/dev/vdb'],check=True)
root=Path('/mnt/storage');root.mkdir(exist_ok=True);subprocess.run(['mount','/dev/vdb',str(root)],check=True);os.chown(root,1000,1000)
with tarfile.open('/home/admin/lan-server-kit.tar.gz') as archive:
 for item in archive.getmembers():assert not item.issym() and not item.islnk() and not item.name.startswith('/') and '..' not in Path(item.name).parts
 archive.extractall(root,filter='data')
kit=root/'DATA-ARK-RECOVERY';sys.path.insert(0,str(kit));import bootstrap_stock_pi as b
config=json.loads((kit/'site.json').read_text());assert config['platform_profile']=='debian13-arm64-lan'
assert 'network-manager' not in config['packages']
plan=b.platforms.proposal(config,b.platforms.discover());errors=b.preflight(config,kit,Path('/var/lib/dataark/bootstrap.json'))+plan['issues'];assert not errors,errors
password=secrets.token_urlsafe(24);secret=Path('/root/lan-acceptance-caretaker');secret.write_text(password);secret.chmod(0o600)
report={'status':'running','started_at':time.time(),'profile':config['platform_profile'],'source_revision':json.loads((kit/'kit.json').read_text())['source_revision'],'real_cli':True,'network_before':before,'phases_retried':False}
(state/'result.json').write_text(json.dumps(report,indent=2))
child,fd=pty.fork()
if child==0:os.execv('/usr/bin/python3',['python3',str(kit/'bootstrap_stock_pi.py'),'--kit',str(kit),'--accept-plan',plan['plan_id'],'--apply'])
answers=[(b'Type INSTALL',b'INSTALL\n'),(b'Create a separate network administration password',password.encode()+b'\n'),(b'Repeat password:',password.encode()+b'\n')];buffer=b'';deadline=time.monotonic()+2400
with Path('/var/log/ark-lan-install.log').open('wb') as log:
 while True:
  if time.monotonic()>deadline:raise TimeoutError('Installer exceeded 40 minutes')
  ready,_,_=select.select([fd],[],[],2)
  if ready:
   try:data=os.read(fd,65536)
   except OSError:break
   if not data:break
   log.write(data.replace(password.encode(),b'[redacted]'));log.flush();buffer=(buffer+data)[-10000:]
   if answers and answers[0][0] in buffer:
    os.write(fd,answers.pop(0)[1]);buffer=b''
  pid,status=os.waitpid(child,os.WNOHANG)
  if pid:break
try:_,status=os.waitpid(child,0)
except ChildProcessError:pass
code=os.waitstatus_to_exitcode(status);report.update(exit_code=code,finished_at=time.time(),network_after=network_snapshot());report['network_unchanged']=report['network_before']==report['network_after'];report['status']='installed' if code==0 and report['network_unchanged'] else 'failed';(state/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['network_before','network_after']}))
raise SystemExit(code or (not report['network_unchanged']))

