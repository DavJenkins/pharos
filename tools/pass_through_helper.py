#!/usr/bin/python3
"""Fixed-scope AP forwarding control. Installed root-owned; JSON input only."""
import ipaddress
import json
import re
import subprocess
import sys

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wifi_interfaces import interfaces

NFT = '/usr/sbin/nft'
IP = '/usr/sbin/ip'

def run(args, **kwargs):
    return subprocess.run(args, **kwargs, capture_output=True, text=True, timeout=5, check=True).stdout


def execute(data):
    if not isinstance(data, dict) or set(data) - {'address','enabled'}:
        raise ValueError('Invalid request')
    address = ipaddress.IPv4Address(data.get('address',''))
    if address not in ipaddress.IPv4Network('192.168.4.0/24') or address.packed[-1] in (0,1,255):
        raise ValueError('Expected an AP client address')
    requested = data.get('enabled')
    if requested is not None and type(requested) is not bool:
        raise ValueError('Invalid switch state')
    table = json.loads(run([NFT,'-j','list','table','inet','dataark_forward']))
    sets = {item['set']['name']:item['set'] for item in table['nftables'] if 'set' in item}
    if set(sets) != {'clients','addresses'}:
        raise ValueError('Forwarding control unavailable')
    neighbors = json.loads(run([IP,'-j','neigh','show','to',str(address),'dev',interfaces()[0]]))
    macs = {row.get('lladdr','').lower() for row in neighbors
            if row.get('dst') == str(address) and row.get('dev',interfaces()[0]) == 'wlan0'}
    if len(macs) != 1 or not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',next(iter(macs),'')):
        if requested is not None:
            raise ValueError('Device address unavailable; reconnect to the AP and retry')
        return {'enabled':False}
    mac = next(iter(macs))
    def values(name):
        found = set()
        for element in sets[name].get('elem',[]):
            if isinstance(element,str): found.add(element)
            elif isinstance(element,dict) and isinstance(element.get('elem'),dict):
                found.add(element['elem'].get('val'))
            else: raise ValueError('Unrecognized forwarding state')
        return found
    clients, addresses = values('clients'), values('addresses')
    enabled = mac in clients and str(address) in addresses
    if requested is not None:
        commands = []
        for name, value, present in (('clients',mac,mac in clients),('addresses',str(address),str(address) in addresses)):
            if requested != present:
                action = 'add' if requested else 'delete'
                commands.append(f'{action} element inet dataark_forward {name} {{ {value} }}')
        if commands: run([NFT,'-f','-'],input='\n'.join(commands)+'\n')
        enabled = requested
    return {'enabled':enabled}


def main():
    import fcntl
    try:
        raw = sys.stdin.buffer.read(1025)
        if len(raw) > 1024 or len(sys.argv) != 1:
            raise ValueError('Invalid request')
        with open('/run/dataark-pass-through.lock','w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            result = execute(json.loads(raw))
        print(json.dumps({'ok':True,**result}))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps({'ok':False,'error':'Pass-through control unavailable; check the installation and AP connection.'}))
        sys.exit(1)

if __name__ == '__main__':
    main()
