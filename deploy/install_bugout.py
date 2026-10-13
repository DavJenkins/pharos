#!/usr/bin/env python3
"""Install optional bugout worker; no copies start and no HA events are sent here."""
import argparse
import getpass
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
from urllib.parse import urlsplit
from install_network_admin import install

ROOT = Path(__file__).resolve().parents[1]
UNIT = """[Unit]
Description=Data Ark household bugout snapshots
After=network.target

[Service]
Type=simple
User=admin
Group=admin
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -u /opt/dataark/tools/bugout_worker.py
Restart=on-failure
RestartSec=5
UMask=0077
RuntimeDirectory=dataark-bugout
RuntimeDirectoryMode=0700
StateDirectory=dataark/bugout
StateDirectoryMode=0700
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/mnt/storage /var/lib/dataark/bugout /run/dataark-bugout
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure-ha',action='store_true')
    parser.add_argument('--rotate-token',action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0 or ROOT != Path('/opt/dataark'):
        raise SystemExit('Run sudo python3 deploy/install_bugout.py on the Pi.')
    os.umask(0o077)
    for command in ('smbclient','gpg','curl','tar','systemctl'):
        if not shutil.which(command):
            raise SystemExit('Install missing dependency first: sudo apt install smbclient gnupg curl tar')
    if not (ROOT/'venv/bin/python').is_file() or not Path('/etc/dataark/network-admin.json').is_file():
        raise SystemExit('Install the API and network administration password first.')
    account = pwd.getpwnam('admin')
    directory = Path('/etc/dataark')
    credentials = directory/'bugout-ha.json'
    if directory.is_symlink() or credentials.is_symlink():
        raise SystemExit('Refusing symlink configuration.')
    config = json.loads(credentials.read_text()) if credentials.exists() else {}
    token = None
    if not config.get('inbound_token_sha256') or args.rotate_token:
        token = secrets.token_urlsafe(32)
        config['inbound_token_sha256'] = hashlib.sha256(token.encode()).hexdigest()
    if args.configure_ha:
        address = input('Home Assistant base URL (blank disables outbound events): ').strip().rstrip('/')
        if address:
            parsed = urlsplit(address)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
                raise SystemExit('Use an HTTP(S) base URL without a path, credentials or query.')
            config['url'] = address
            config['token'] = getpass.getpass('Home Assistant long-lived access token: ')
            if not config['token'] or any(ord(c)<32 for c in config['token']):
                raise SystemExit('Invalid token.')
        else:
            config.pop('url',None);config.pop('token',None)
    unit = Path('/etc/systemd/system/dataark-bugout.service')
    if unit.exists() and 'Data Ark household bugout snapshots' not in unit.read_text():
        raise SystemExit('Refusing an unmanaged service file.')
    # Do not stop an active copy just to reinstall its service definition.
    state = Path('/var/lib/dataark/bugout')
    if (state/'state.sqlite').exists():
        import sqlite3
        with sqlite3.connect(state/'state.sqlite') as db:
            if db.execute("SELECT count(*) FROM operations WHERE state IN ('queued','running')").fetchone()[0]:
                raise SystemExit('A bugout operation is active. Wait for it to finish before reinstalling.')
    for folder in (state,state/'credentials',state/'gnupg',directory/'bugout-keys'):
        if folder.is_symlink():
            raise SystemExit('Refusing symlink directory: '+str(folder))
        folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        if folder != directory/'bugout-keys':
            os.chown(folder,account.pw_uid,account.pw_gid)
            folder.chmod(0o700)
        else:
            os.chown(folder,0,account.pw_gid);folder.chmod(0o750)
    install(credentials,json.dumps(config).encode(),0o640,account.pw_gid)
    install(unit,UNIT.encode(),0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','dataark-bugout.service'],check=True)
    if token:
        print('Save this token privately in HA secrets.yaml; it is shown only once:')
        print('Bearer '+token)
    print('Worker installed. No backup tasks were started.')
    print('Configure bugout.tasks in dataark.yaml, deploy the web page, then restart dataark.service.')
    print('Configure optional outbound HA events later with --configure-ha.')


if __name__ == '__main__':
    main()
