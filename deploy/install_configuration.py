#!/usr/bin/env python3
"""Install the fixed configuration publisher; does not change configuration."""
import os,pwd,subprocess
from pathlib import Path

UNIT='''[Unit]
Description=Publish validated Data Ark content configuration
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/opt/dataark/venv/bin/python /opt/dataark/tools/publish_configuration.py
TimeoutStartSec=420
UMask=0077
'''

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Run as root on the Ark.')
    account=pwd.getpwnam('admin');folder=Path('/var/lib/dataark/configuration');folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700);os.chown(folder,account.pw_uid,account.pw_gid)
    unit=Path('/etc/systemd/system/dataark-configuration-publish.service');unit.write_text(UNIT);unit.chmod(0o644)
    subprocess.run(['systemd-analyze','verify',str(unit)],check=True);subprocess.run(['systemctl','daemon-reload'],check=True)
