#!/usr/bin/python3
"""Install the signed software updater. Does not apply updates or enroll keys."""
import json
import argparse
import os
from pathlib import Path
import pwd
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from software_update import Updater,atomic

ROOT=Path(__file__).resolve().parents[1]
UNITS={
'dataark-software-update.service':'''[Unit]
Description=Apply a verified Data Ark software package
After=network.target
OnFailure=dataark-software-recover.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-software-update --worker
TimeoutStartSec=300
UMask=0077
''',
'dataark-software-recover.service':'''[Unit]
Description=Recover an interrupted Data Ark software transaction
After=network.target
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-software-update --recover
TimeoutStartSec=180
UMask=0077
''',
'dataark-software-boot-recover.service':'''[Unit]
Description=Restore interrupted Ark software before starting the API
After=local-fs.target
Before=dataark.service
ConditionPathExists=!/run/dataark-software-update-active
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-software-update --boot-recover
RemainAfterExit=yes
UMask=0077
''',
'dataark-software-verify-recovery.service':'''[Unit]
Description=Verify recovered Ark software
After=dataark.service apache2.service
Wants=dataark.service apache2.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-software-update --verify-recovery
TimeoutStartSec=90
[Install]
WantedBy=multi-user.target
'''}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',help='Explicit source revision for a reviewed legacy installation without build metadata');parser.add_argument('--profile',choices=['raspberry-pi-debian13-arm64','debian13-arm64-lan','debian13-amd64-lan']);args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('Run as root on the Ark')
    os.umask(0o077);account=pwd.getpwnam('admin')
    for name in ('software_update.py','software_update_control.py'):
        raw=(ROOT/'tools'/name).read_bytes();compile(raw,name,'exec')
        target=Path('/usr/local/libexec')/('dataark-software-update' if name.endswith('control.py') else name)
        atomic(target,raw,0o755 if name.endswith('control.py') else 0o644);os.chown(target,0,0)
    updater=Updater();updater.state.chmod(0o700);os.chown(updater.state,0,0)
    updater.trust.mkdir(parents=True,exist_ok=True);updater.trust.chmod(0o755);os.chown(updater.trust,0,0)
    inbox=Path('/var/lib/dataark/software-inbox');inbox.mkdir(parents=True,exist_ok=True);inbox.chmod(0o700);os.chown(inbox,account.pw_uid,account.pw_gid)
    # Enroll exactly the deployed, generated files. Later edits must be reviewed.
    if not (updater.state/'installed.json').exists():
        build=json.loads(Path('/opt/dataark/app/static/assets/build-info.json').read_text())
        try:profile=args.profile or json.loads(Path('/etc/dataark/platform.json').read_text())['profile']
        except (OSError,ValueError,KeyError):
            model=Path('/proc/device-tree/model')
            if model.exists() and model.read_text().startswith('Raspberry Pi'):profile='raspberry-pi-debian13-arm64'
            else:raise SystemExit('Supply the reviewed --profile for this legacy installation')
        updater.enroll(args.revision or build['revision'],profile)
    public=ROOT/'config/software-update-release-key.pem'
    if public.is_file():
        subprocess.run(['openssl','pkey','-pubin','-in',str(public),'-noout'],check=True,capture_output=True)
        atomic(updater.trust/'dej-release.pem',public.read_bytes(),0o644)
    for name,content in UNITS.items():atomic(Path('/etc/systemd/system')/name,content.encode(),0o644)
    dropin=Path('/etc/systemd/system/dataark.service.d/software-recovery.conf')
    atomic(dropin,b'[Unit]\nRequires=dataark-software-boot-recover.service\nAfter=dataark-software-boot-recover.service\n',0o644)
    rule=b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-software-update ""\n'
    check=updater.state/'sudoers-check';atomic(check,rule)
    subprocess.run(['/usr/sbin/visudo','-cf',str(check)],check=True,capture_output=True)
    atomic(Path('/etc/sudoers.d/dataark-software-update'),rule,0o440);check.unlink()
    subprocess.run(['systemd-analyze','verify',*[str(Path('/etc/systemd/system')/name) for name in UNITS]],check=True,capture_output=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','dataark-software-verify-recovery.service'],check=True,capture_output=True)
    print('Signed software updater installed. No signing keys enrolled and no updates applied.')

if __name__=='__main__':main()
