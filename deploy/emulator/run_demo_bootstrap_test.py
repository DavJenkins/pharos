#!/usr/bin/python3
"""Run the actual demo bootstrap once in a marked, disposable ARM64 QEMU guest.

Requires candidate-kit.tar.gz in /home/admin and no existing Ark installation.
Uses the coordinator's CLI, plan approval and real terminal/password prompts.
No software phases, source checks or installer guards are bypassed.
"""
from pathlib import Path
import os,sys,tarfile,json,hashlib,subprocess,time,secrets,pty,select,re,signal
base=Path('/var/lib/dataark/acceptance/clean-demo-20261101');base.mkdir(parents=True,exist_ok=False)
assert os.geteuid()==0 and Path('/etc/dataark-clean-bootstrap-test').is_file()
model=Path('/sys/firmware/devicetree/base/model').read_text().replace('\x00','')
assert 'dummy-virt' in model or 'QEMU' in model
assert not Path('/opt/dataark').exists() and not Path('/var/lib/dataark/bootstrap.json').exists()
assert subprocess.check_output(['findmnt','-n','-o','SOURCE','/'],text=True).strip().startswith('/dev/vda')
kitroot=Path('/home/admin/demo-candidate');kitroot.mkdir()
with tarfile.open('/home/admin/candidate-kit.tar.gz') as archive:archive.extractall(kitroot,filter='data')
kit=kitroot/'DATA-ARK-RECOVERY';meta=json.loads((kit/'kit.json').read_text());digest=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
files=[p for p in kit.rglob('*') if p.is_file()];before={str(p.relative_to(kit)):digest(p) for p in files}
command=['python3',str(kit/'bootstrap_stock_pi.py'),'--kit',str(kit),'--profile','debian13-arm64-lan','--demo-library-gib','4']
preview=subprocess.run(command,capture_output=True,text=True);(base/'preview.log').write_text(preview.stdout+preview.stderr)
if preview.returncode or 'BLOCKED:' in preview.stdout:raise SystemExit('Preview blocked; inspect preview.log')
plan=re.findall(r'"plan_id":\s*"([a-f0-9]+)"',preview.stdout)[-1]
report={'status':'running','started_at':time.time(),'source_revision':meta['source_revision'],'source_sha256':meta['source_sha256'],'coordinator_invocations':1,'manual_corrections':[],'profile':'debian13-arm64-lan','demo_gib':4,'no_content_disk':True,'kit_before':before,'plan_id':plan,'boot_before':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def save():(base/'result.json').write_text(json.dumps(report,indent=2))
save();password=secrets.token_urlsafe(24);secret=Path('/root/demo-test-caretaker');secret.write_text(password);secret.chmod(0o600)
pid,fd=pty.fork()
if pid==0:os.execvp(command[0],command+['--accept-plan',plan,'--apply'])
log=(base/'install.log').open('w');pending='';sent=set();started=time.monotonic()
try:
 while True:
  ready,_,_=select.select([fd],[],[],1)
  if ready:
   try:data=os.read(fd,65536)
   except OSError:break
   if not data:break
   text=data.decode(errors='replace');log.write(text.replace(password,'[redacted]'));log.flush();pending=(pending+text)[-10000:]
   for key,prompt,value in [('install','Type INSTALL to apply this reviewed plan:','INSTALL'),('create','Create a separate network administration password (12+ characters):',password),('repeat','Repeat password:',password)]:
    if key not in sent and prompt in pending:
     os.write(fd,(value+'\n').encode());sent.add(key)
  if time.monotonic()-started>5400:
   os.kill(pid,signal.SIGTERM);report['timeout']=True;break
 _,status=os.waitpid(pid,0);report['exit_code']=os.waitstatus_to_exitcode(status)
finally:log.close();os.close(fd)
report['kit_after']={str(p.relative_to(kit)):digest(p) for p in files};report['kit_unchanged']=report['kit_before']==report['kit_after'];report['finished_at']=time.time();report['status']='passed' if report.get('exit_code')==0 and report['kit_unchanged'] else 'failed';save()
print(report['status'],flush=True)
