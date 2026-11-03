#!/usr/bin/env python3
"""Bind VNC only to currently assigned private IPv4 addresses on physical network interfaces."""
import ipaddress, json, os, subprocess, time
from pathlib import Path

def wait_for_desktop(runtime=None, display=None):
    socket=Path(runtime or os.environ.get('XDG_RUNTIME_DIR','/run/user/1000'))/(display or os.environ.get('WAYLAND_DISPLAY','wayland-0'))
    if not socket.is_socket():
        print('Waiting for the local desktop login before starting VNC.',flush=True)
    while not socket.is_socket():time.sleep(5)

if __name__ == '__main__':wait_for_desktop()
addresses=[]
for interface in json.loads(subprocess.check_output(['/usr/sbin/ip','-j','address'],text=True)):
    if not interface['ifname'].startswith(('wl','eth','en')): continue
    for value in interface.get('addr_info',[]):
        if value.get('family')!='inet':continue
        address=ipaddress.ip_address(value['local'])
        if any(address in network for network in map(ipaddress.ip_network,['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])):
            addresses.append(str(address))
if not addresses:raise SystemExit('No hotspot/private LAN IPv4 address is available yet')
os.execv('/usr/bin/wayvnc',['wayvnc','-C','/home/admin/.config/dataark-vnc/config','-f','15','-n','Data Ark desktop']+sorted(set(addresses)))
