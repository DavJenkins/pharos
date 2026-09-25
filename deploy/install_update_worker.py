#!/usr/bin/env python3
"""Install the Data Ark automatic content update service and timer."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICE = '''[Unit]
Description=Data Ark automatic content updates
After=network-online.target docker.service
Wants=network-online.target
ConditionPathIsMountPoint=/mnt/storage

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -u /opt/dataark/tools/update_worker.py
StateDirectory=dataark/updates
StateDirectoryMode=0755
UMask=0022
Nice=10
IOSchedulingClass=idle
TimeoutStartSec=infinity
TimeoutStopSec=45
KillMode=control-group
'''
TIMER = '''[Unit]
Description=Check Data Ark content update queue

[Timer]
OnBootSec=2min
OnUnitInactiveSec=5min
AccuracySec=30s
Unit=dataark-update.service

[Install]
WantedBy=timers.target
'''


def install(path, text):
    if path.is_symlink():
        raise RuntimeError('Refusing symlink: ' + str(path))
    if path.exists():
        backup = path.with_suffix(path.suffix + '.before-dataark')
        if not backup.exists():
            shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(text.encode())
    try:
        temp.chmod(0o644)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or ROOT != Path('/opt/dataark'):
        raise SystemExit('Run sudo python3 deploy/install_update_worker.py from the Pi repository at /opt/dataark.')
    for name in ('curl', 'docker', 'systemctl', 'rsync'):
        if shutil.which(name) is None:
            raise SystemExit('Required program missing: ' + name)
    subprocess.run([str(ROOT/'venv/bin/python'), '-c',
        'from app.services.manifest import load_manifest; from tools.update_worker import source_config; d=load_manifest("dataark.yaml"); [source_config(a) for a in d["assets"] if a.get("update_policy") != "manual" and a.get("refresh_interval") != "never"]'], cwd=ROOT, check=True)
    units = Path('/etc/systemd/system')
    install(units/'dataark-update.service', SERVICE)
    install(units/'dataark-update.timer', TIMER)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','dataark-update.timer'],check=True)
    print('Automatic update timer enabled. Due assets are checked every five minutes; manifest refresh intervals control release discovery.')
    print('Logs: journalctl -u dataark-update.service -f')
    print('Pause: sudo systemctl stop dataark-update.timer dataark-update.service')
    print('Partial downloads are retained and resume when the timer is started again.')

if __name__ == '__main__':
    main()