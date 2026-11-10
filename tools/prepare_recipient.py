#!/usr/bin/env python3
"""Prepare an installed, content-preserving Ark for a new owner.

Arming does not change the running machine. The next boot replaces device and
SSH identities and removes provisioner SSH access. Password setup works through the hotspot or local terminal.
"""
import argparse
import getpass
import hmac
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import uuid
import time
import re
import configparser
import html

HELPER = '/usr/local/libexec/dataark-recipient'
STATE = '/var/lib/dataark/recipient.json'
UNIT = '''[Unit]
Description=Establish a unique Data Ark recipient identity
After=local-fs.target
Before=network-pre.target NetworkManager.service ssh.service dataark-https-reconcile.service dataark.service
Wants=network-pre.target
ConditionPathExists=/var/lib/dataark/recipient-armed

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/libexec/dataark-recipient --first-boot
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
'''
DESKTOP = '''[Desktop Entry]
Type=Application
Name=Set up Data Ark
Comment=Choose this Ark's caretaker password locally
Exec=lxterminal -t "Data Ark setup" -e "sudo /usr/bin/python3 /usr/local/libexec/dataark-recipient --set-password"
Icon=preferences-system
Terminal=false
'''


def write(path, text, mode=0o600):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Unexpected symlink: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.recipient-new')
    with temp.open('w',encoding='utf-8') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    temp.chmod(mode);temp.replace(path)


def save(root,value):write(root/STATE.lstrip('/'),json.dumps(value,indent=2)+'\n',0o644)


def password_record(password):
    if not 12 <= len(password) <= 256:raise ValueError('Use 12-256 characters.')
    salt=secrets.token_bytes(16)
    return {'salt':salt.hex(),'hash':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,300000).hex()}


def inspection(root=Path('/')):
    """Describe ownership preparation without changing identity or credentials."""
    blockers=[]
    marked=(root/'etc/dataark-physical-bootstrap-test').is_file()
    managed=(root/'etc/systemd/system/dataark.service').is_file() and (root/'etc/dataark/network-admin.json').is_file()
    if not marked and not managed:blockers.append('A managed Data Ark installation is required.')
    demo=root/'var/lib/dataark/demo-library.json'
    if demo.exists() and json.loads(demo.read_text()).get('stage')!='ready':blockers.append('Finish system-card library preparation first.')
    for name in ('bugout-ha.json','https/active.json'):
        path=root/'etc/dataark'/name
        if path.exists():
            data=json.loads(path.read_text())
            if any(data.get(k) for k in ('token','url','domain','inbound_token_sha256')):
                blockers.append('Configured integration/certificate must be removed before recipient preparation: '+name)
    for relative in ('etc/dataark/household-secrets.json','etc/dataark/ha-outbound.json','root/.ssh/id_rsa','root/.ssh/id_ed25519','home/admin/.ssh/id_rsa','home/admin/.ssh/id_ed25519'):
        if (root/relative).exists():blockers.append('Review and remove owner-private file before handoff: /'+relative)
    def contains_secret(value):
        if isinstance(value,dict):return any((str(k).lower() in ('password','token','secret','private_key','api_key','authorization','inbound_token_sha256') and bool(v)) or contains_secret(v) for k,v in value.items())
        if isinstance(value,list):return any(contains_secret(v) for v in value)
        return False
    for path in (root/'etc/dataark').rglob('*.json'):
        if path.name in ('network-admin.json','device-identity.json'):continue
        try:data=json.loads(path.read_text())
        except (ValueError,UnicodeError):continue
        if contains_secret(data):
            note='Remove or reconfigure owner credentials before handoff: /'+path.relative_to(root).as_posix()
            if note not in blockers:blockers.append(note)
    for relative in ('etc/dataark/https/installed','etc/dataark/https/acme'):
        folder=root/relative
        if folder.exists() and any(folder.iterdir()):blockers.append('Private certificate/ACME material must be retired: /'+relative)
    site=root/'opt/dataark/config/installed-site.json'
    settings=json.loads(site.read_text()) if site.exists() else {}
    profile=settings.get('platform_profile','')
    mode='lan' if str(profile).endswith('-lan') else 'hotspot'
    ssid=settings.get('hotspot',{}).get('ssid','DataArk')
    for path in (root/'etc/NetworkManager/system-connections').glob('*'):
        if not path.is_file() or path.is_symlink():continue
        config=configparser.ConfigParser(interpolation=None,strict=False)
        try:config.read_string(path.read_text())
        except (ValueError,configparser.Error,UnicodeError):continue
        if any(config.has_section(section) for section in ('vpn','wireguard','802-1x')):blockers.append('Review private network authentication before handoff: '+path.name)
        if config.get('ipv4','method',fallback='')=='shared':ssid=config.get('wifi','ssid',fallback=config.get('802-11-wireless','ssid',fallback=ssid))
    result={'eligible':not blockers,'blockers':blockers,'network_mode':mode,'hotspot_ssid':ssid,
            'layout':'system-card library' if demo.exists() and not settings.get('external_library') else 'external library or LAN server',
            'changes':['New machine/Ark identity, hostname and SSH host keys on next boot','Remove provisioner login keys and cloud-init access','Replace caretaker and Linux account credentials through recipient setup','Remove saved upstream Wi-Fi profiles; preserve the local hotspot','Keep public library content and configuration'],
            'personal_review':'Review Linux home/browser files and private household data before giving the entire system to another owner. This is identity preparation, not a secure disk wipe.'}
    result['plan_id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result

def validate(root):
    result=inspection(root)
    if result['blockers']:raise ValueError(' '.join(result['blockers']))
    armed=root/'var/lib/dataark/recipient-armed'
    if armed.exists():raise ValueError('Recipient setup is already armed.')


def arm(root=Path('/'), runner=subprocess.run, code=None, hostname=None):
    code=code or f'{secrets.randbelow(10000):04d}'
    if not re.fullmatch('[0-9]{4}',code):raise ValueError('Pairing code must have four digits.')
    if hostname is not None and (not isinstance(hostname,str) or not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]',hostname)):raise ValueError('Invalid recipient hostname')
    validate(root)
    if root==Path('/') and not (root/'var/www/html/setup.html').is_file():raise ValueError('Install the recipient web setup page/API before arming.')
    # Install a root-owned immutable copy, independent of the writable repository.
    write(root/HELPER.lstrip('/'),Path(__file__).read_text(),0o755)
    write(root/'etc/systemd/system/dataark-recipient.service',UNIT,0o644)
    write(root/'home/admin/.config/autostart/dataark-recipient.desktop',DESKTOP,0o644)
    write(root/'home/admin/Desktop/Set up Data Ark.desktop',DESKTOP,0o755)
    if root==Path('/'):
        import pwd
        account=pwd.getpwnam('admin')
        for relative in ('home/admin/.config/autostart/dataark-recipient.desktop','home/admin/Desktop/Set up Data Ark.desktop'):
            os.chown(root/relative,account.pw_uid,account.pw_gid)
    write(root/'root/dataark-recipient-setup-code',code+'\n')
    write(root/'var/lib/dataark/recipient-enrollment.json',json.dumps({'code_sha256':hashlib.sha256(code.encode()).hexdigest()})+'\n')
    machine=uuid.uuid4().hex
    save(root,{'state':'armed','password_setup':'one-time pairing code in a browser, or local terminal','content_preserved':True,
               'machine_id':machine,'device_id':'ark-'+uuid.uuid4().hex[:16],'hostname':hostname or 'dataark-'+machine[:6],
               'network_mode':inspection(root)['network_mode'],'hotspot_ssid':inspection(root)['hotspot_ssid']})
    write(root/'var/lib/dataark/recipient-armed','armed\n')
    if root==Path('/'):
        runner(['systemctl','daemon-reload'],check=True)
        runner(['systemctl','enable','dataark-recipient.service'],check=True)
        rule='admin ALL=(root) NOPASSWD: /usr/bin/python3 /usr/local/libexec/dataark-recipient --enroll\n'
        check=root/'run/dataark-recipient-sudoers';write(check,rule,0o440)
        runner(['visudo','-cf',str(check)],check=True)
        write(root/'etc/sudoers.d/dataark-recipient',rule,0o440);check.unlink()


def first_boot(root=Path('/'),runner=subprocess.run):
    marker=root/'var/lib/dataark/recipient-armed'
    if not marker.is_file():return
    blockers=inspection(root)['blockers']
    if blockers:raise ValueError(' '.join(blockers))
    # A certificate could have been configured after the card was armed.
    active=root/'etc/dataark/https/active.json'
    if active.exists() and json.loads(active.read_text()).get('domain'):
        raise ValueError('Remove this owner certificate before recipient identity setup; HTTP remains available.')
    # A retry reuses the chosen identity instead of generating another one.
    state_path=root/STATE.lstrip('/')
    state=json.loads(state_path.read_text())
    state.setdefault('machine_id',uuid.uuid4().hex)
    state.setdefault('device_id','ark-'+uuid.uuid4().hex[:16])
    state.setdefault('hostname','dataark-'+state['machine_id'][:6])
    state['state']='establishing_identity';save(root,state)
    write(root/'etc/machine-id',state['machine_id']+'\n',0o444)
    dbus=root/'var/lib/dbus/machine-id'
    if dbus.is_symlink():dbus.unlink()
    write(dbus,state['machine_id']+'\n',0o444)
    write(root/'etc/hostname',state['hostname']+'\n',0o644)
    hosts=root/'etc/hosts';lines=hosts.read_text().splitlines()
    lines=[line for line in lines if line.split()[:1]!=['127.0.1.1']]
    write(hosts,'\n'.join(lines)+'\n127.0.1.1 '+state['hostname']+'\n',0o644)
    cloud=root/'etc/cloud/cloud.cfg.d'
    if cloud.is_dir():write(cloud/'99-dataark-hostname.cfg','preserve_hostname: true\nmanage_etc_hosts: false\n',0o644)
    write(root/'etc/dataark/device-identity.json',json.dumps({'device_id':state['device_id']})+'\n')
    # A new owner must not receive queued notifications belonging to the sender.
    import sqlite3
    for relative,table in [('var/lib/dataark/bugout/state.sqlite','events'),('var/lib/dataark/bugout/setup-security/events.sqlite3','alerts')]:
        path=root/relative
        if path.is_file() and not path.is_symlink():
            with sqlite3.connect(path,timeout=3) as db:
                if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():db.execute('DELETE FROM '+table)
    # No inherited caretaker password or remote provisioner access survives.
    credentials=root/'etc/dataark/network-admin.json'
    write(credentials,json.dumps(password_record(secrets.token_urlsafe(48)))+'\n',0o640)
    if root==Path('/'):os.chown(credentials,0,__import__('grp').getgrnam('admin').gr_gid)
    for home in (root/'root',root/'home/admin'):
        (home/'.ssh/authorized_keys').unlink(missing_ok=True)
    for key in (root/'etc/ssh').glob('ssh_host_*'):key.unlink()
    (root/'var/lib/NetworkManager/secret_key').unlink(missing_ok=True)
    for profile in (root/'etc/NetworkManager/system-connections').glob('*'):
        if not profile.is_file() or profile.is_symlink():continue
        config=configparser.ConfigParser(interpolation=None,strict=False)
        try:config.read_string(profile.read_text())
        except (ValueError,configparser.Error,UnicodeError):continue
        if config.get('connection','type',fallback='') in ('wifi','802-11-wireless') and config.get('ipv4','method',fallback='')!='shared':
            profile.unlink()
        elif config.has_section('connection'):
            config.set('connection','uuid',str(uuid.uuid4()))
            import io
            stream=io.StringIO();config.write(stream);write(profile,stream.getvalue())
    (root/'var/lib/systemd/random-seed').unlink(missing_ok=True)
    # Cloud-init must not restore the original provisioner's key on a later boot.
    for relative in ('boot/firmware/user-data','var/lib/cloud/seed/nocloud/user-data','var/lib/cloud/seed/nocloud-net/user-data'):
        p=root/relative
        if p.is_file():write(p,'#cloud-config\n{}\n')
    write(root/'etc/cloud/cloud-init.disabled','Recipient identity is owned by Data Ark.\n')
    for relative in ('root/physical-demo-test-caretaker','root/.bash_history','home/admin/.bash_history'):
        (root/relative).unlink(missing_ok=True)
    (root/'boot/firmware/dataark-card/provision.json').unlink(missing_ok=True)
    if root==Path('/'):
        runner(['usermod','--lock','admin'],check=True,capture_output=True)
        runner(['usermod','--lock','root'],check=True,capture_output=True)
        write(root/'etc/ssh/sshd_config.d/00-dataark-recipient.conf','PasswordAuthentication no\nPermitRootLogin no\n',0o644)
        runner(['hostname',state['hostname']],check=True)
        runner(['ssh-keygen','-A'],check=True)
    state['state']='awaiting_local_password';save(root,state)
    marker.unlink()


def welcome_sheet(root=Path('/')):
    """Private printable sheet. Never place it in the public library."""
    state=json.loads((root/STATE.lstrip('/')).read_text())
    code=(root/'root/dataark-recipient-setup-code').read_text().strip()
    from app.services.welcome_guides import render
    demo=root/'var/lib/dataark/demo-library.json'
    channel='microsd' if demo.exists() else 'appliance'
    return render(channel,code=code,hostname=state['hostname'],ssid=state.get('hotspot_ssid','DataArk'),network_mode=state.get('network_mode','hotspot'),root=root/'opt/dataark')



def complete_password(password,admin_password,root=Path('/')):
    state_path=root/STATE.lstrip('/');state=json.loads(state_path.read_text())
    if state['state']!='awaiting_local_password':raise ValueError('Recipient setup is not pending.')
    password_record(password)
    password_record(admin_password)
    if any(ord(c)<32 or ord(c)==127 for c in admin_password):raise ValueError('Account password cannot contain control characters.')
    if root==Path('/'):
        subprocess.run(['chpasswd'],input='admin:'+admin_password+'\n',text=True,check=True,capture_output=True)
        subprocess.run(['usermod','--lock','root'],check=True,capture_output=True)
        ssh_config=root/'etc/ssh/sshd_config.d/00-dataark-recipient.conf'
        write(ssh_config,'# Recipient can administer a headless Ark.\nPasswordAuthentication yes\nPermitRootLogin no\n',0o644)
        subprocess.run(['sshd','-t'],check=True,capture_output=True)
        subprocess.run(['systemctl','reload','ssh'],check=True,capture_output=True)
    credentials=root/'etc/dataark/network-admin.json'
    write(credentials,json.dumps(password_record(password))+'\n',0o640)
    if root==Path('/'):os.chown(credentials,0,__import__('grp').getgrnam('admin').gr_gid)
    state['state']='ready';save(root,state)
    for relative in ('var/lib/dataark/recipient-enrollment.json','root/dataark-recipient-setup-code','home/admin/.config/autostart/dataark-recipient.desktop','home/admin/Desktop/Set up Data Ark.desktop'):
        (root/relative).unlink(missing_ok=True)


def enroll(data,root=Path('/')):
    state=json.loads((root/STATE.lstrip('/')).read_text())
    if state.get('state')!='awaiting_local_password':raise ValueError('Recipient setup is not pending.')
    if not isinstance(data,dict) or set(data)!={'code','password','admin_password'} or not all(isinstance(v,str) for v in data.values()):raise ValueError('Setup code and password required.')
    record_path=root/'var/lib/dataark/recipient-enrollment.json'
    record=json.loads(record_path.read_text())
    now=time.time()
    if record.get('retry_after',0)>now:
        if root==Path('/'):
            import syslog
            syslog.syslog(syslog.LOG_WARNING,'Data Ark first-owner setup: request rejected during code cooldown')
        raise ValueError('Too many incorrect codes. Wait one minute and try again.')
    if not re.fullmatch(r'[0-9]{4}',data['code']) or not hmac.compare_digest(hashlib.sha256(data['code'].encode()).hexdigest(),record['code_sha256']):
        record['failures']=record.get('failures',0)+1
        if record['failures']>=5:record.update(failures=0,retry_after=now+60)
        write(record_path,json.dumps(record)+'\n')
        if root==Path('/'):
            import syslog
            syslog.syslog(syslog.LOG_WARNING,'Data Ark first-owner setup: incorrect setup code')
        raise ValueError('Setup code not accepted.')
    password_record(data['password'])
    complete_password(data['password'],data['admin_password'],root)
    return {'ok':True,'state':'ready'}


def set_password(root=Path('/')):
    state_path=root/STATE.lstrip('/');state=json.loads(state_path.read_text())
    if state['state']!='awaiting_local_password':raise ValueError('No recipient password setup is pending.')
    if not os.isatty(0):raise ValueError('Use the local interactive terminal.')
    # A headless browser may finish enrollment while this terminal waits.
    import threading,signal
    stop=threading.Event()
    def watch_completion():
        while not stop.wait(1):
            try:finished=json.loads(state_path.read_text()).get('state')=='ready'
            except (OSError,ValueError):continue
            if finished:
                print('\nSetup was completed in another window. Closing this prompt.',flush=True)
                os.kill(os.getpid(),signal.SIGTERM)
                return
    threading.Thread(target=watch_completion,daemon=True).start()
    print('Welcome to your Data Ark. Its library works without internet.\nChoose a caretaker password for changes to the Ark; browsing needs no password.')
    password=getpass.getpass('New caretaker password (12+ characters): ')
    if password != getpass.getpass('Repeat password: '):raise ValueError('Passwords did not match; run setup again.')
    admin_password=getpass.getpass('New Linux admin account password (12+ characters): ')
    if admin_password!=getpass.getpass('Repeat admin account password: '):raise ValueError('Account passwords did not match.')
    stop.set()
    if root==Path('/'):
        import fcntl
        lock=Path('/run/dataark-recipient-enroll.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
    complete_password(password,admin_password,root)
    print('Ready. Open Data Ark to browse your library. Username for caretaker actions: admin.')
    input('Press Enter to close. ')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--arm',action='store_true');group.add_argument('--first-boot',action='store_true');group.add_argument('--set-password',action='store_true');group.add_argument('--enroll',action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('Run with sudo.')
    if args.arm:
        print('The NEXT BOOT replaces machine/SSH identities and removes provisioner SSH keys. Content is kept. Recipient password setup works through the hotspot with the supplied setup code, or locally.')
        if input('Type PREPARE RECIPIENT: ')!='PREPARE RECIPIENT':raise SystemExit('Cancelled.')
        arm();print('Armed. Give the recipient the code saved in /root/dataark-recipient-setup-code. Shut down before mailing; the next boot establishes its identity.')
    elif args.first_boot:first_boot()
    elif args.enroll:
        import sys,fcntl
        lock=Path('/run/dataark-recipient-enroll.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            body=sys.stdin.read(4097)
            if len(body)>4096:raise ValueError('Request too large.')
            print(json.dumps(enroll(json.loads(body))))
        except ValueError as error:
            cooldown='Wait one minute' in str(error)
            kind='cooldown' if cooldown else 'code_rejected' if str(error)=='Setup code not accepted.' else 'setup_not_pending' if str(error)=='Recipient setup is not pending.' else 'invalid_request'
            print(json.dumps({'ok':False,'cooldown':cooldown,'security_event':kind,'error':'Too many incorrect codes. Wait one minute and try again.' if cooldown else 'Setup code/password not accepted, or setup is already complete.'}))
        except (OSError,KeyError,subprocess.CalledProcessError):print(json.dumps({'ok':False,'error':'Setup could not complete. Try again or use the local terminal.'}))
    else:set_password()

if __name__=='__main__':main()
