#!/usr/bin/env python3
"""Install the read-only reference publisher checker."""
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deploy.install_update_worker import install

SERVICE = '''[Unit]
Description=Data Ark reference publisher checks
After=network-online.target
Wants=network-online.target
ConditionPathIsMountPoint=/mnt/storage

[Service]
Type=oneshot
User=admin
Group=admin
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -u /opt/dataark/tools/check_reference_sources.py
StateDirectory=dataark/reference-checks
StateDirectoryMode=0755
Nice=10
CPUWeight=10
IOWeight=10
MemoryMax=256M
TimeoutStartSec=6h
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadOnlyPaths=/mnt/storage /opt/dataark
'''
TIMER = '''[Unit]
Description=Schedule Data Ark reference publisher checks
[Timer]
OnBootSec=4min
OnUnitInactiveSec=1h
RandomizedDelaySec=2min
Unit=dataark-reference-checks.service
[Install]
WantedBy=timers.target
'''

def main():
    if os.geteuid() != 0: raise SystemExit('Run as root on the Ark')
    for name, content in [('service', SERVICE), ('timer', TIMER)]:
        install(Path('/etc/systemd/system/dataark-reference-checks.' + name), content)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'dataark-reference-checks.timer'], check=True)

if __name__ == '__main__': main()
