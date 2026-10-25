#!/usr/bin/env python3
"""Retain bounded local system logs so unexpected reboot investigations have evidence."""
from pathlib import Path
import os,subprocess

def install():
    if os.geteuid()!=0:raise SystemExit('Run with sudo.')
    folder=Path('/etc/systemd/journald.conf.d');folder.mkdir(parents=True,exist_ok=True)
    config=folder/'dataark-reliability.conf'
    content='[Journal]\nStorage=persistent\nSystemMaxUse=64M\nRuntimeMaxUse=16M\nSystemKeepFree=512M\nMaxRetentionSec=7day\nSyncIntervalSec=30s\n'
    if config.exists() and config.read_text()!=content:
        backup=Path('/var/backups/dataark-reliability');backup.mkdir(parents=True,exist_ok=True,mode=0o700)
        (backup/'previous-journald.conf').write_text(config.read_text())
    config.write_text(content);config.chmod(0o644)
    Path('/var/log/journal').mkdir(parents=True,exist_ok=True)
    subprocess.run(['systemd-tmpfiles','--create','--prefix=/var/log/journal'],check=True)
    subprocess.run(['systemctl','restart','systemd-journald'],check=True)
    subprocess.run(['journalctl','--flush'],check=True)
    print('Persistent local journal enabled: 64 MiB / seven days; watchdog and network settings unchanged.')
if __name__=='__main__':install()
