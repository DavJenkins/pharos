#!/usr/bin/env python3
"""Install anonymous read-only FTP after the Debian vsftpd package is installed."""
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]

def main():
    if os.geteuid()!=0:
        raise SystemExit('Run with sudo python3 deploy/install_ftp.py')
    if not Path('/usr/sbin/vsftpd').is_file() or not Path('/mnt/storage').is_mount():
        raise SystemExit('Install Debian vsftpd and mount the content SSD first.')
    backup=Path('/var/backups/dataark-ftp')/datetime.now().strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True,mode=0o700)
    for name in ('vsftpd.conf','dataark.conf'):
        target=Path('/etc/vsftpd.conf') if name=='vsftpd.conf' else Path('/etc/systemd/system/vsftpd.service.d/dataark.conf')
        if target.is_symlink():
            raise SystemExit('Refusing symlink configuration target')
        if target.exists():
            shutil.copy2(target,backup/name)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'deploy/ftp'/name,target)
        os.chown(target,0,0);target.chmod(0o644)
    for directory in ('/srv/dataark-ftp','/srv/dataark-ftp/library'):
        p=Path(directory)
        if p.is_symlink():
            raise SystemExit('Refusing symlink FTP root')
        p.mkdir(parents=True,exist_ok=True);os.chown(p,0,0);p.chmod(0o755)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','vsftpd'],check=True)
    subprocess.run(['systemctl','restart','vsftpd'],check=True)
    print('Anonymous read-only FTP configured. Verify listing, resume, blocked writes and private-path exclusion.')
if __name__=='__main__':
    main()
