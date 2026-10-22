#!/usr/bin/env python3
"""Install optional bounded portal diagnostics controlled by the Ark Debug setting."""
from pathlib import Path
import os, shutil, subprocess, datetime
ROOT=Path(__file__).resolve().parents[1]
UNIT='[Unit]\nDescription=Data Ark bounded captive portal connection diagnostics\nAfter=NetworkManager.service\nWants=NetworkManager.service\n\n[Service]\nType=simple\nExecStart=/usr/local/libexec/dataark-portal-monitor\nRestart=on-failure\nRestartSec=10\nUMask=0077\nNice=10\nCPUQuota=5%\nMemoryMax=64M\nNoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\nReadWritePaths=/var/log/dataark-portal-monitor\nCapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN\nStandardOutput=null\nStandardError=journal\n\n[Install]\nWantedBy=multi-user.target\n'
def main():
    if os.geteuid()!=0 or ROOT!=Path('/opt/dataark'):
        raise SystemExit('Run sudo python3 deploy/install_portal_monitor.py on the Ark.')
    if not shutil.which('tcpdump'):raise SystemExit('tcpdump is required')
    backup=Path('/var/backups/dataark-portal-monitor')/datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True)
    log=Path('/var/log/dataark-portal-monitor');log.mkdir(mode=0o700,exist_ok=True);log.chmod(0o700)
    target=Path('/usr/local/libexec/dataark-portal-monitor');target.parent.mkdir(parents=True,exist_ok=True)
    unit=Path('/etc/systemd/system/dataark-portal-monitor.service')
    for path in [target,unit]:
        if path.exists():shutil.copy2(path,backup/path.name)
    shutil.copy2(ROOT/'tools/portal_monitor.py',target);target.chmod(0o700)
    unit.write_text(UNIT);unit.chmod(0o644)
    subprocess.run(['systemd-analyze','verify',str(unit)],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',unit.name],check=True)
    subprocess.run(['systemctl','restart',unit.name],check=True)
    print('Debug-controlled diagnostics installed. Backup:',backup)
if __name__=='__main__':main()
