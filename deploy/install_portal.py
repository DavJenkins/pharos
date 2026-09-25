#!/usr/bin/env python3
"""Install AP-only welcome detection without interrupting NetworkManager or Docker."""
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import struct
import time
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
MARKER = '# Managed by Data Ark portal v1'
UNIT = 'dataark-portal-dns.service'
HOSTS = ('connectivitycheck.gstatic.com', 'connectivitycheck.android.com',
         'captive.apple.com', 'www.msftconnecttest.com', 'www.msftncsi.com')
LEGACY = shlex.split('-A PREROUTING -i wlan0 -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 80')
DNS = MARKER + '''
port=1053
interface=wlan0
listen-address=192.168.4.1
except-interface=lo
bind-dynamic
no-resolv
no-hosts
server=192.168.4.1#53
cache-size=150
local-ttl=30
user=dnsmasq
'''
for host in HOSTS:
    DNS += f'address=/{host}/192.168.4.1\nlocal=/{host}/\n'
NFT = MARKER + '''
add table ip dataark_portal
flush table ip dataark_portal
add chain ip dataark_portal dns { type nat hook prerouting priority -110; policy accept; }
add rule ip dataark_portal dns iifname "wlan0" ip saddr 192.168.4.0/24 ip daddr 192.168.4.1 udp dport 53 redirect to :1053
add rule ip dataark_portal dns iifname "wlan0" ip saddr 192.168.4.0/24 ip daddr 192.168.4.1 tcp dport 53 redirect to :1053
'''
APACHE = MARKER + r'''
# Overwrite client-supplied values; the backend is bound to loopback only.
RequestHeader set X-DataArk-Peer "expr=%{CONN_REMOTE_ADDR}"
RequestHeader unset X-DataArk-Server
ProxyPassMatch "^/(generate_204|gen_204|hotspot-detect\.html|library/test/success\.html|connecttest\.txt|ncsi\.txt)$" "http://127.0.0.1:8000/portal/probe/$1" connectiontimeout=3 timeout=8
'''
SERVICE = MARKER + '''
[Unit]
Description=Data Ark AP welcome DNS
After=NetworkManager.service netfilter-persistent.service dataark.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStartPre=/usr/sbin/dnsmasq --test --conf-file=/etc/dataark/portal-dns.conf
ExecStart=/usr/sbin/dnsmasq --keep-in-foreground --conf-file=/etc/dataark/portal-dns.conf --pid-file=
ExecStartPost=/usr/sbin/nft -f /etc/dataark/portal.nft
ExecStopPost=-/usr/sbin/nft delete table ip dataark_portal
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectHome=yes
ProtectSystem=strict
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
'''
FILES = {
    Path('/etc/dataark/portal-dns.conf'): DNS,
    Path('/etc/dataark/portal.nft'): NFT,
    Path('/etc/apache2/conf-available/dataark-portal.conf'): APACHE,
    Path('/etc/systemd/system') / UNIT: SERVICE,
}
ENABLED = Path('/etc/apache2/conf-enabled/dataark-portal.conf')
SAVED = Path('/etc/iptables/rules.v4')


def run(args, *, check=True, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45, **kwargs)
    if check and result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr.strip()} {result.stdout.strip()}')
    return result


def atomic(path, data, mode=0o644):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(data)
    try:
        temp.chmod(mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def clean_saved(text):
    table = None
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith('*'):
            table = line.strip()
        if table == '*nat' and shlex.split(line) == LEGACY:
            continue
        lines.append(line)
    return ''.join(lines)


def live_legacy_positions(text):
    position = 0
    found = []
    for line in text.splitlines():
        tokens = shlex.split(line)
        if tokens[:2] == ['-A', 'PREROUTING']:
            position += 1
            if tokens == LEGACY:
                found.append(position)
    return found


def rollback(backup):
    meta = json.loads((backup/'state.json').read_text())
    run(['systemctl','stop',UNIT], check=False)
    if not meta['enabled']:
        run(['systemctl','disable',UNIT], check=False)
    for filename, item in meta['files'].items():
        path = Path(filename)
        if item is None:
            path.unlink(missing_ok=True)
        else:
            atomic(path, (backup/item['backup']).read_bytes(), item['mode'])
    if not meta['apache_enabled']:
        ENABLED.unlink(missing_ok=True)
    current = live_legacy_positions(run(['iptables','-t','nat','-S','PREROUTING']).stdout)
    for _ in current:
        run(['iptables','-w','5','-t','nat','-D',*LEGACY[1:]])
    for position in meta['legacy_positions']:
        run(['iptables','-w','5','-t','nat','-I','PREROUTING',str(position),*LEGACY[2:]])
    if not meta['headers_enabled']:
        run(['a2dismod','headers'], check=False)
    run(['systemctl','daemon-reload'])
    if meta['enabled']:
        run(['systemctl','enable',UNIT])
    if meta['active']:
        run(['systemctl','start',UNIT])
    run(['apache2ctl','configtest'])
    run(['systemctl','reload','apache2'])
    print(f'Restored portal configuration from {backup}')


def wait_for_api():
    # systemctl restart can return before a Type=simple application binds its socket.
    for attempt in range(21):
        listeners = run(['ss','-H','-ltn','sport = :8000']).stdout.splitlines()
        if listeners:
            endpoints = [line.split()[3] if len(line.split()) >= 5 else '<unrecognized ss output>'
                         for line in listeners]
            if any(endpoint != '127.0.0.1:8000' for endpoint in endpoints):
                raise SystemExit('The API must listen only on 127.0.0.1:8000. Found: ' + ', '.join(endpoints))
            return
        if attempt < 20:
            time.sleep(.5)
    raise SystemExit('No API listener appeared on port 8000 within 10 seconds. '
                     'Check systemctl status dataark.service and journalctl -u dataark.service -n 30 --no-pager. '
                     'No portal configuration was changed.')


def check_dns():
    # Query the dedicated listener, not the Pi's own resolver.
    hostname = HOSTS[0]
    question = b"".join(bytes([len(label)]) + label.encode() for label in hostname.split('.')) + b"\x00\x00\x01\x00\x01"
    packet = struct.pack('!6H', 0xDA41, 0x0100, 1, 0, 0, 0) + question
    for _ in range(5):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)
                sock.connect(('192.168.4.1',1053))
                sock.send(packet)
                reply = sock.recv(4096)
            ident, flags, questions, answers, _, _ = struct.unpack('!6H',reply[:12])
            if ident == 0xDA41 and flags & 15 == 0 and answers == 1 and reply.endswith(socket.inet_aton('192.168.4.1')):
                return
        except (OSError, struct.error):
            pass
        time.sleep(.2)
    raise RuntimeError('The AP portal DNS listener did not return its expected address.')


def main():
    import argparse
    import pwd
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0 or ROOT != Path('/opt/dataark'):
        raise SystemExit('Run sudo python3 deploy/install_portal.py from /opt/dataark on the Pi.')
    if args.rollback:
        backup = args.rollback.resolve()
        if backup.parent != Path('/var/backups/dataark-portal') or backup.stat().st_uid != 0:
            raise SystemExit('Use a root-owned backup printed by this installer.')
        rollback(backup)
        return
    for name in ('dnsmasq','nft','iptables','apache2ctl','a2enmod','a2dismod','curl','nmcli','ss'):
        if shutil.which(name) is None:
            raise SystemExit('Required program missing: '+name)
    pwd.getpwnam('dnsmasq')
    profile = run(['nmcli','-g','connection.interface-name,ipv4.method,ipv4.addresses,802-11-wireless.mode','connection','show','DataArk']).stdout.splitlines()
    if profile != ['wlan0','shared','192.168.4.1/24','ap']:
        raise SystemExit('Unexpected DataArk AP profile; no changes made.')
    wait_for_api()
    ports = run(['ss','-H','-lunt','sport = :1053']).stdout
    unit_path = Path('/etc/systemd/system')/UNIT
    if ports and not (unit_path.exists() and unit_path.read_bytes() == SERVICE.encode()):
        raise SystemExit('Port 1053 is in use by another configuration.')
    for path in [*FILES, SAVED]:
        if path.is_symlink():
            raise SystemExit('Unexpected configuration symlink: '+str(path))
        if path in FILES and path.exists() and not path.read_text().startswith(MARKER):
            raise SystemExit('Refusing unmanaged file: '+str(path))
    if ENABLED.exists() or ENABLED.is_symlink():
        if not ENABLED.is_symlink() or ENABLED.resolve() != Path('/etc/apache2/conf-available/dataark-portal.conf'):
            raise SystemExit('Unexpected Apache enabled configuration.')
    if not unit_path.exists() and run(['nft','list','table','ip','dataark_portal'],check=False).returncode == 0:
        raise SystemExit('An unmanaged dataark_portal firewall table already exists.')
    modules = run(['apache2ctl','-M']).stdout
    if any(m not in modules for m in ('proxy_module','proxy_http_module')):
        raise SystemExit('The existing Apache reverse-proxy modules must be enabled.')
    with tempfile.NamedTemporaryFile(mode='w') as test:
        test.write(DNS); test.flush()
        run(['dnsmasq','--test','--conf-file='+test.name])
    run(['nft','-c','-f','-'], input=NFT)
    base = Path('/var/backups/dataark-portal')
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=base))
    meta = {
        'files': {}, 'apache_enabled': ENABLED.is_symlink(),
        'headers_enabled': 'headers_module' in modules,
        'enabled': run(['systemctl','is-enabled','--quiet',UNIT],check=False).returncode == 0,
        'active': run(['systemctl','is-active','--quiet',UNIT],check=False).returncode == 0,
        'legacy_positions': live_legacy_positions(run(['iptables','-t','nat','-S','PREROUTING']).stdout),
    }
    for i,path in enumerate([*FILES,SAVED]):
        meta['files'][str(path)] = None
        if path.exists():
            name = str(i)
            (backup/name).write_bytes(path.read_bytes())
            meta['files'][str(path)] = {'backup':name, 'mode':path.stat().st_mode & 0o777}
    (backup/'state.json').write_text(json.dumps(meta,indent=2))
    print(f'Configuration backup: {backup}',flush=True)
    try:
        for path,text in FILES.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic(path,text.encode())
        if not meta['apache_enabled']:
            ENABLED.symlink_to('/etc/apache2/conf-available/dataark-portal.conf')
        if not meta['headers_enabled']:
            run(['a2enmod','headers'])
        run(['apache2ctl','configtest'])
        run(['systemctl','reload','apache2'])
        result = run(['curl','--noproxy','*','--interface','192.168.4.1','--max-time','8',
                      '--silent','--output','/dev/null','--write-out','%{http_code}',
                      'http://192.168.4.1/generate_204']).stdout
        if result != '302':
            raise RuntimeError('Portal probe did not redirect; deploy and restart the updated API first.')
        run(['systemctl','daemon-reload'])
        run(['systemctl','enable',UNIT])
        run(['systemctl','restart',UNIT])
        run(['systemctl','is-active','--quiet',UNIT])
        check_dns()
        for _ in meta['legacy_positions']:
            run(['iptables','-w','5','-t','nat','-D',*LEGACY[1:]])
        if SAVED.exists():
            atomic(SAVED, clean_saved(SAVED.read_text()).encode(), SAVED.stat().st_mode & 0o777)
    except Exception:
        rollback(backup)
        raise
    print('AP welcome detection installed; normal HTTP/HTTPS internet forwarding is retained.')
    print('NetworkManager, wlan0/wlan1 connections and Docker were not restarted.')
    print('Join the AP on a phone and test the sign-in prompt, then Continue with internet access.')
    print(f'Undo: sudo python3 deploy/install_portal.py --rollback {backup}')

if __name__ == '__main__':
    main()
