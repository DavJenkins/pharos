#!/usr/bin/python3
"""Sender's unattended card build. A successful build powers off for handoff.

Uses only the reviewed kit, explicit library allocation and a private seed.
No provisioner SSH key, common account password or automatic large restore.
"""
from pathlib import Path
import hashlib,json,os,pty,re,select,secrets,signal,subprocess,sys,tarfile,time

BOOT=Path('/boot/firmware/dataark-card')
STATE=Path('/var/lib/dataark/card-build')

def save(phase,**fields):
    STATE.mkdir(parents=True,exist_ok=True);data={'phase':phase,'updated':time.time(),**fields}
    text=json.dumps(data,indent=2)+'\n';p=STATE/'status.new';p.write_text(text);p.replace(STATE/'status.json')
    (BOOT/'result.json').write_text(text)

def extract(archive,destination):
    with tarfile.open(archive) as source:
        members=source.getmembers()
        if sum(m.size for m in members)>1024**3:raise ValueError('Kit is too large')
        for m in members:
            p=Path(m.name)
            if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()):raise ValueError('Unsafe kit member')
        source.extractall(destination,members=members,filter='data')

def install(command,plan,password,log_path):
    pid,fd=pty.fork()
    if pid==0:os.execvp(command[0],command+['--accept-plan',plan,'--apply'])
    pending='';sent=set();started=time.monotonic()
    with log_path.open('a') as log:
        try:
            while True:
                ready,_,_=select.select([fd],[],[],1)
                if ready:
                    try:data=os.read(fd,65536)
                    except OSError:break
                    if not data:break
                    text=data.decode(errors='replace');log.write(text.replace(password,'[private]'));log.flush();pending=(pending+text)[-12000:]
                    prompts=[('install','Type INSTALL to apply this reviewed plan:','INSTALL'),('password','Create a separate network administration password (12+ characters):',password),('repeat','Repeat password:',password)]
                    for key,prompt,value in prompts:
                        if key not in sent and prompt in pending:os.write(fd,(value+'\n').encode());sent.add(key)
                if time.monotonic()-started>3*3600:os.kill(pid,signal.SIGTERM);raise ValueError('Installation timed out; inspect the retained journal')
            _,status=os.waitpid(pid,0)
            if os.waitstatus_to_exitcode(status)!=0:raise ValueError('Installation stopped; the source kit and logs are retained')
        finally:os.close(fd)

def main():
    if os.geteuid()!=0:raise ValueError('Card build requires root')
    if (STATE/'ready').exists():return
    # Recover the tiny power-loss window after arming but before writing ready.
    recipient=Path('/var/lib/dataark/recipient.json');bootstrap=Path('/var/lib/dataark/bootstrap.json')
    if recipient.exists() and bootstrap.exists() and 'finish' in json.loads(bootstrap.read_text()).get('completed',[]) and json.loads(recipient.read_text()).get('state') in ('armed','establishing_identity','awaiting_local_password','ready'):
        STATE.mkdir(parents=True,exist_ok=True);(STATE/'ready').write_text('ready\n');return
    seed=json.loads((BOOT/'provision.json').read_text());archive=BOOT/'kit.tar.gz'
    with archive.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
    if checksum!=seed['kit_sha256']:raise ValueError('Seeded kit checksum differs')
    if not re.fullmatch('[0-9]{4}',seed['pairing_code']) or not re.fullmatch('dataark-[a-f0-9]{12}',seed['hostname']):raise ValueError('Invalid private card seed')
    if type(seed['library_gib']) is not int or not 2<=seed['library_gib']<=1024:raise ValueError('Invalid library allocation')
    ready=STATE/'status.json'
    if ready.exists() and json.loads(ready.read_text()).get('phase')=='ready':return
    save('installing',message='Building this card. Internet is needed until ready; no optional collection restore is started.')
    kitroot=Path('/home/admin/dataark-card-kit');kitroot.mkdir(parents=True,exist_ok=True)
    if not (kitroot/'DATA-ARK-RECOVERY/kit.json').exists():extract(archive,kitroot)
    kit=kitroot/'DATA-ARK-RECOVERY';site=kit/'site.json';settings=json.loads(site.read_text())
    settings['wifi_country']=seed['country'];site.write_text(json.dumps(settings,indent=2)+'\n')
    command=['python3',str(kit/'bootstrap_stock_pi.py'),'--kit',str(kit),'--profile','raspberry-pi-debian13-arm64','--demo-library-gib',str(seed['library_gib'])]
    preview=subprocess.run(command,capture_output=True,text=True)
    (STATE/'preview.log').write_text(preview.stdout+preview.stderr)
    if preview.returncode or 'BLOCKED:' in preview.stdout:raise ValueError('Installation review was blocked; inspect preview.log')
    plans=re.findall(r'"plan_id":\s*"([a-f0-9]{64})"',preview.stdout)
    if not plans:raise ValueError('No reviewed installation plan')
    secret=STATE/'temporary-caretaker';password=secret.read_text().strip() if secret.exists() else secrets.token_urlsafe(32)
    secret.write_text(password);secret.chmod(0o600)
    install(command,plans[-1],password,STATE/'install.log')
    subprocess.run(['curl','--fail','--silent','http://127.0.0.1/api/'],check=True,stdout=subprocess.DEVNULL)
    sys.path.insert(0,'/opt/dataark')
    from tools.prepare_recipient import arm
    arm(code=seed['pairing_code'],hostname=seed['hostname'])
    secret.unlink(missing_ok=True)
    save('ready',message='Card built and prepared for its recipient. Automatic power-off follows. The next boot is first-owner setup; keep the private welcome sheet.')
    (STATE/'ready').write_text('ready\n')
    subprocess.run(['sync'],check=True);subprocess.run(['shutdown','-h','now'],check=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        save('failed',message=str(e));raise
