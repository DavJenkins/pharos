#!/usr/bin/env python3
"""One-time root-owned helper installation. Does not change network connections."""
import argparse
import getpass
import grp
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

def install(path, content, mode, gid=0):
    if path.is_symlink():
        raise SystemExit(f'Refusing symlink destination: {path}')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(content)
    try:
        temp.chmod(mode)
        os.chown(temp, 0, gid)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset-password', action='store_true', help='Replace the administration password after entering and confirming a new one.')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo python3 deploy/install_network_admin.py')
    os.umask(0o077)
    source = Path(__file__).resolve().parents[1] / 'tools/network_helper.py'
    helper = source.read_bytes()
    compile(helper, str(source), 'exec')
    for command in ('/usr/bin/nmcli', '/usr/sbin/visudo', '/usr/bin/sudo'):
        if not Path(command).is_file():
            raise SystemExit(f'Required command missing: {command}')
    account = subprocess.run(['systemctl', 'show', 'dataark.service', '-p', 'User', '--value'],
                             capture_output=True, text=True, check=True).stdout.strip()
    if account != 'admin':
        raise SystemExit('Expected dataark.service to run as admin; inspect its service unit.')
    gid = grp.getgrnam('admin').gr_gid
    directory = Path('/etc/dataark')
    credentials = directory / 'network-admin.json'
    new_credentials = None
    if args.reset_password or not credentials.exists():
        password = getpass.getpass('Create a separate network administration password (12+ characters): ')
        confirmation = getpass.getpass('Repeat password: ')
        if password != confirmation or not 12 <= len(password) <= 256:
            raise SystemExit('Passwords must match and contain 12–256 characters.')
        salt = secrets.token_bytes(16)
        new_credentials = json.dumps({'salt': salt.hex(), 'hash': hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 300000).hex()}).encode()
    else:
        print('Keeping the existing network administration password.')
    rule = b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-network ""\n'
    with tempfile.NamedTemporaryFile() as check:
        check.write(rule)
        check.flush()
        subprocess.run(['/usr/sbin/visudo', '-cf', check.name], check=True, stdout=subprocess.DEVNULL)
    for folder, mode in ((directory, 0o750), (Path('/usr/local/libexec'), 0o755)):
        if folder.is_symlink():
            raise SystemExit(f'Refusing symlink directory: {folder}')
        folder.mkdir(parents=True, exist_ok=True, mode=mode)
        if folder == directory:
            os.chown(folder, 0, gid)
            folder.chmod(mode)
    subprocess.run(['/usr/bin/python3',str(source.parents[1]/'deploy/install_wifi_roles.py')],check=True)
    support=(source.parent/'support_diagnostics.py').read_bytes()
    compile(support,'support_diagnostics.py','exec')
    install(Path('/usr/local/libexec/dataark-support-diagnostics'),support,0o755)
    install(Path('/usr/local/libexec/dataark-network'), helper, 0o755)
    if new_credentials is not None:
        install(credentials, new_credentials, 0o640, gid)
    install(Path('/etc/sudoers.d/dataark-network'), rule, 0o440)
    print('Installed the fixed-scope network helper and authentication configuration.')
    print('No network connections were changed. Username: admin.')
    print('Deploy/restart the API, then open /config/wifi.html or /config/system.html.')

if __name__ == '__main__':
    main()
