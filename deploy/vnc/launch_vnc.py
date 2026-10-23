#!/usr/bin/env python3
"""Bind VNC only to currently assigned private IPv4 addresses on physical network interfaces."""
import ipaddress, json, os, subprocess
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
