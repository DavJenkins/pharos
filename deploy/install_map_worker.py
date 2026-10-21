#!/usr/bin/env python3
"""Install independent, low-priority map collection; does not restart Ark services."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deploy.install_update_worker import install
SERVICE="""[Unit]
Description=Data Ark local reference map collection
After=network-online.target
Wants=network-online.target
ConditionPathIsMountPoint=/mnt/storage

[Service]
Type=oneshot
User=admin
Group=admin
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -u /opt/dataark/tools/map_worker.py
StateDirectory=dataark/maps
StateDirectoryMode=0700
UMask=0022
Nice=10
IOSchedulingClass=idle
TimeoutStartSec=6h
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/mnt/storage /var/lib/dataark/maps
"""
TIMER="""[Unit]
Description=Process due Data Ark maps and retry incomplete downloads

[Timer]
OnActiveSec=1min
OnUnitInactiveSec=1d
Persistent=true
Unit=dataark-maps.service

[Install]
WantedBy=timers.target
"""
def main():
    if os.geteuid()!=0 or ROOT!=Path('/opt/dataark'):
        raise SystemExit('Run sudo python3 deploy/install_map_worker.py on the Pi at /opt/dataark.')
    subprocess.run([str(ROOT/'venv/bin/python'),'-c',
        'from app.services.manifest import load_manifest; from tools.map_worker import settings; d=load_manifest("dataark.yaml"); settings(d); assert d["system"]["base_mount"]=="/mnt/storage"'],cwd=ROOT,check=True)
    if subprocess.run(['systemctl','show','-p','ActiveState','--value','dataark-maps.service'],capture_output=True,text=True,check=True).stdout.strip() in ('active','activating','deactivating','reloading'):
        raise SystemExit('Wait for active map collection before reinstalling its unit.')
    subprocess.run(['runuser','-u','admin','--',str(ROOT/'venv/bin/python'),str(ROOT/'tools/map_worker.py'),'--initialize'],cwd=ROOT,check=True)
    units=Path('/etc/systemd/system')
    install(units/'dataark-maps.service',SERVICE);install(units/'dataark-maps.timer',TIMER)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','dataark-maps.timer'],check=True)
    print('Map collection enabled; first run in about one minute. Metadata checks follow maps.refresh_days; incomplete files retry daily.')
    print('Status: /library-files/maps/index.html; logs: journalctl -u dataark-maps.service')
    print('Pause: sudo systemctl stop dataark-maps.timer dataark-maps.service')
if __name__=='__main__':main()
