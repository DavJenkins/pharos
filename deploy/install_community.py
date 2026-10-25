#!/usr/bin/env python3
"""Install private board storage and daily backups. Does not grant root privileges."""
import os
from pathlib import Path
import pwd
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    if os.geteuid()!=0:raise SystemExit('Run sudo python3 deploy/install_community.py')
    account=pwd.getpwnam('admin')
    for folder in [Path('/var/lib/dataark/community'),Path('/var/backups/dataark-community')]:
        if folder.is_symlink():raise SystemExit('Refusing symlink: '+str(folder))
        folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chown(folder,account.pw_uid,account.pw_gid);folder.chmod(0o700)
    subprocess.run(['runuser','-u','admin','--',str(ROOT/'venv/bin/python'),'-B','-c',
                    'from app.services.community import initialize; initialize()'],cwd=ROOT,check=True)
    units={
      'dataark-community-backup.service':'''[Unit]
Description=Private Data Ark community board snapshot
After=dataark.service
[Service]
Type=oneshot
User=admin
Group=admin
UMask=0077
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -B /opt/dataark/tools/backup_community.py
''',
      'dataark-community-backup.timer':'''[Unit]
Description=Daily Data Ark community board backup
[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=5m
[Install]
WantedBy=timers.target
'''}
    for name,content in units.items():
        path=Path('/etc/systemd/system')/name
        if path.is_symlink():raise SystemExit('Refusing symlink: '+str(path))
        path.write_text(content);path.chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','dataark-community-backup.timer'],check=True)
    subprocess.run(['systemctl','start','dataark-community-backup.service'],check=True)
    print('Community board storage and daily private backups installed. Restart dataark after adding the router.')

if __name__=='__main__':main()
