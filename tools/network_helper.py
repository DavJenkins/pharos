#!/usr/bin/python3 -I
"""Root-owned, fixed-scope NetworkManager helper. One JSON request on stdin."""
import json
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wifi_interfaces import interfaces

NMCLI = '/usr/bin/nmcli'
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'}

class NetworkError(Exception):
    pass

def nm(*args, timeout=5):
    try:
        result = subprocess.run([NMCLI, '--wait', str(timeout), *args],
                                capture_output=True, text=True, timeout=timeout + 3,
                                env=ENV, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        raise NetworkError('NetworkManager did not respond in time.') from None
    if result.returncode:
        # Never return raw command output: it may contain credentials or HTML.
        raise NetworkError('NetworkManager rejected the operation.')
    return result.stdout.rstrip('\n')

def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    action = data.get('action')
    allowed = {'scan': {'action'}, 'connect': {'action', 'ssid', 'security', 'password'},
               'rename': {'action', 'ssid'}, 'uplink': {'action', 'enabled'}, 'ethernet': {'action', 'enabled'}, 'hotspot': {'action', 'enabled'}, 'access': {'action'}, 'adapters': {'action'}, 'diagnostics': {'action'}, 'publish-configuration': {'action'}, 'assign': {'action','adapter'}, 'confirm-roles': {'action'}, 'revert-roles': {'action'}}
    for fields in allowed.values():
        fields.update({'peer'})
    if action not in allowed or set(data) - allowed[action]:
        raise ValueError('Unsupported network operation.')
    if action in ('uplink', 'ethernet', 'hotspot') and type(data.get('enabled')) is not bool:
        raise ValueError('Enabled must be true or false.')
    if action == 'assign' and not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', str(data.get('adapter',''))):
        raise ValueError('Choose an adapter from the hardware list.')
    if action not in ('scan', 'access', 'uplink', 'ethernet', 'hotspot', 'adapters', 'assign', 'confirm-roles', 'revert-roles', 'diagnostics', 'publish-configuration'):
        ssid = data.get('ssid')
        if not isinstance(ssid, str) or not 1 <= len(ssid.encode('utf-8')) <= 32:
            raise ValueError('Network names must contain 1 to 32 UTF-8 bytes.')
        if any(ord(c) < 32 or ord(c) == 127 for c in ssid):
            raise ValueError('Network names cannot contain control characters.')
    if action == 'connect':
        password = data.get('password', '')
        security = data.get('security')
        if not isinstance(password, str) or any(ord(c) < 32 or ord(c) == 127 for c in password):
            raise ValueError('Invalid Wi-Fi password.')
        if security == 'open':
            if password:
                raise ValueError('Open networks do not use a password.')
        elif security == 'wpa-psk':
            if not (8 <= len(password.encode('utf-8')) <= 63 or re.fullmatch(r'[0-9a-fA-F]{64}', password)):
                raise ValueError('Use an 8–63 byte WPA passphrase or 64 hexadecimal digits.')
        else:
            raise ValueError('Only open and WPA/WPA2 Personal networks are supported.')
    return action

def ap_details():
    mode = nm('-g', '802-11-wireless.mode', 'connection', 'show', 'id', 'DataArk')
    device = nm('-g', 'connection.interface-name', 'connection', 'show', 'id', 'DataArk')
    if mode != 'ap' or device != interfaces()[0]:
        raise NetworkError('DataArk is not the expected access-point profile.')
    return nm('--escape', 'no', '-g', '802-11-wireless.ssid', 'connection', 'show', 'id', 'DataArk')

def access_interfaces(data):
    try:
        peer = ipaddress.ip_address(data.get('peer', ''))
    except ValueError:
        raise NetworkError('Cannot determine your access path. Reopen the Ark directly through a known network address.') from None
    protected = set()
    local_interfaces = {}
    for interface in dict.fromkeys([v for v in (*interfaces(),'eth0') if v]):
        addresses = nm('-g', 'IP4.ADDRESS,IP6.ADDRESS', 'device', 'show', interface)
        for address in addresses.splitlines():
            try: local = ipaddress.ip_interface(address)
            except ValueError: continue
            local_interfaces[str(local.ip)] = interface
            if interface == interfaces()[0] and peer in local.network:
                protected.add(interface)
    try:
        # Kernel socket records identify the receiving interface without trusting Host or forwarded server headers.
        sockets = subprocess.run(['/usr/bin/ss','-H','-tn','state','established'],
                                 capture_output=True,text=True,timeout=3,check=True)
        for line in sockets.stdout.splitlines():
            fields = line.split()
            if len(fields) < 4: continue
            local, remote = fields[2], fields[3]
            host, port = local.rsplit(':',1)
            remote_host = remote.rsplit(':',1)[0].strip('[]').split('%')[0]
            if port == '80' and ipaddress.ip_address(remote_host) == peer:
                interface = local_interfaces.get(host.strip('[]').split('%')[0])
                if interface: protected.add(interface)
        route = subprocess.run(['/usr/sbin/ip', '-j', 'route', 'get', str(peer)],
                               capture_output=True,text=True,timeout=3,check=True)
        interface = json.loads(route.stdout)[0].get('dev')
        if interface in (*interfaces(),'eth0'): protected.add(interface)
    except (OSError,ValueError,IndexError,subprocess.SubprocessError):
        raise NetworkError('Cannot verify your connection. No network connection was changed.') from None
    if not protected:
        raise NetworkError('Cannot identify a safe access path. No network connection was changed.')
    return sorted(protected)

def protect_access(data, interface):
    if interface in access_interfaces(data):
        raise NetworkError('This connection is carrying your current session. Connect through another interface before disabling or reconfiguring it.')

def execute(data):
    action = validate(data)
    if action == 'publish-configuration':
        result = subprocess.run(['/usr/bin/systemctl','start','--no-block','dataark-configuration-publish.service'],capture_output=True,text=True,timeout=10,check=False)
        return {'ok':result.returncode==0,'error':'Configuration publisher could not start.'}
    if action == 'diagnostics':
        result = subprocess.run(['/usr/local/libexec/dataark-support-diagnostics'], capture_output=True,text=True,timeout=140,check=False)
        return json.loads(result.stdout)
    if action in ('adapters','assign','confirm-roles','revert-roles'):
        request = {k:v for k,v in data.items() if k != 'peer'}
        result = subprocess.run(['/usr/local/libexec/dataark-wifi-roles'], input=json.dumps(request), capture_output=True, text=True, timeout=140, check=False)
        return json.loads(result.stdout)
    if action not in ('access','scan') and Path('/var/lib/dataark/wifi-roles/pending.json').exists():
        raise NetworkError('Confirm or revert the pending adapter assignment first.')
    if action in ('scan','connect','uplink') and not interfaces()[1]:
        raise NetworkError('No second Wi-Fi adapter is available for upstream Wi-Fi.')
    if action == 'access':
        return {'ok': True, 'protected': access_interfaces(data)}
    if action in ('uplink', 'ethernet', 'hotspot'):
        ap_details()
        interface = {'ethernet':'eth0', 'uplink':interfaces()[1], 'hotspot':interfaces()[0]}[action]
        label = {'ethernet':'Ethernet', 'uplink':'Upstream Wi-Fi', 'hotspot':'Hotspot'}[action]
        # Never use radio wifi off: it also disables the hotspot adapter.
        if data['enabled']:
            nm('connection', 'up', 'id', 'DataArk', 'ifname', interfaces()[0], timeout=30) if action == 'hotspot' else nm('device', 'connect', interface, timeout=30)
        else:
            protect_access(data, interface)
            nm('device', 'disconnect', interface, timeout=15)
        return {'ok': True, 'enabled': data['enabled'],
                'message': label + ' enabled.' if data['enabled'] else
                label + ' disabled until enabled again or the Ark restarts. Saved networks are retained.'}
    if action == 'scan':
        own_ssid = ap_details()
        output = nm('--terse', '--escape', 'no', '--fields', 'SSID', 'device', 'wifi', 'list',
                    'ifname', interfaces()[1], '--rescan', 'yes', timeout=15)
        names = sorted({name for name in output.splitlines() if name and name != '--' and name != own_ssid})
        return {'ok': True, 'networks': names}
    ssid = data['ssid']
    old_ap = ap_details()
    if action == 'rename':
        protect_access(data, interfaces()[0])
        if ssid == old_ap:
            return {'ok': True, 'ssid': ssid, 'message': 'AP name unchanged.'}
        nm('connection', 'modify', 'id', 'DataArk', '802-11-wireless.ssid', ssid)
        try:
            nm('connection', 'up', 'id', 'DataArk', 'ifname', interfaces()[0], timeout=30)
        except NetworkError:
            try:
                nm('connection', 'modify', 'id', 'DataArk', '802-11-wireless.ssid', old_ap)
                nm('connection', 'up', 'id', 'DataArk', 'ifname', interfaces()[0], timeout=30)
            except NetworkError:
                raise NetworkError('AP change failed; automatic recovery failed. Use the Pi console.') from None
            raise NetworkError('AP change failed; the previous AP name was restored.') from None
        return {'ok': True, 'ssid': ssid, 'message': 'AP name updated.'}
    if ssid == old_ap:
        raise ValueError('Choose an upstream network, not this appliance’s own access point.')
    protect_access(data, interfaces()[1])
    previous = nm('-g', 'GENERAL.CON-UUID', 'device', 'show', interfaces()[1])
    connection_id = str(uuid.uuid4())
    args = ['connection', 'add', 'type', 'wifi', 'ifname', interfaces()[1],
            'con-name', 'DataArk-uplink-' + connection_id[:8], 'connection.uuid', connection_id,
            'connection.autoconnect', 'no', '802-11-wireless.ssid', ssid,
            'ipv4.method', 'auto', 'ipv6.method', 'auto']
    if data['security'] == 'wpa-psk':
        args += ['802-11-wireless-security.key-mgmt', 'wpa-psk',
                 '802-11-wireless-security.psk-flags', '0']
    nm(*args)
    try:
        # A private password file avoids exposing the secret in process arguments.
        with tempfile.TemporaryDirectory(prefix='dataark-network-', dir='/run') as directory:
            secret = Path(directory) / 'password'
            secret.write_text('802-11-wireless-security.psk:' + data.get('password', '') + '\n', encoding='utf-8')
            secret.chmod(0o600)
            activate = ['connection', 'up', 'uuid', connection_id, 'ifname', interfaces()[1]]
            if data['security'] == 'wpa-psk':
                activate += ['passwd-file', str(secret)]
            nm(*activate, timeout=30)
        nm('connection', 'modify', 'uuid', connection_id, 'connection.autoconnect', 'yes')
    except (NetworkError, OSError):
        restored = False
        try:
            if re.fullmatch(r'[0-9a-fA-F-]{36}', previous):
                nm('connection', 'up', 'uuid', previous, 'ifname', interfaces()[1], timeout=30)
                restored = True
        except NetworkError:
            pass
        try:
            nm('connection', 'delete', 'uuid', connection_id)
        except NetworkError:
            pass
        suffix = ' Previous connection restored.' if restored else ' Reconnect using the Pi console if needed.'
        raise NetworkError('Wi-Fi connection failed.' + suffix) from None
    return {'ok': True, 'ssid': ssid, 'message': 'Upstream Wi-Fi connected.'}

def main():
    import fcntl
    os.umask(0o077)
    try:
        if os.geteuid() != 0 or len(sys.argv) != 1:
            raise ValueError('Helper must run as root without command-line arguments.')
        raw = sys.stdin.buffer.read(8193)
        if len(raw) > 8192:
            raise ValueError('Request is too large.')
        data = json.loads(raw)
        validate(data)
        lock_dir = Path('/run/dataark-network')
        lock_dir.mkdir(mode=0o700, exist_ok=True)
        with open(lock_dir / 'operation.lock', 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise NetworkError('Another network operation is in progress.') from None
            result = execute(data)
    except (ValueError, UnicodeError, NetworkError) as error:
        result = {'ok': False, 'error': str(error)}
    except Exception:
        result = {'ok': False, 'error': 'Network operation failed; inspect the Pi locally.'}
    print(json.dumps(result))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
