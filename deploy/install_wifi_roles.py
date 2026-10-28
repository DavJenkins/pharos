#!/usr/bin/env python3
"""Install role selection and boot fallback without changing current connections."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UNIT = '''[Unit]
Description=Data Ark Wi-Fi adapter assignment and missing-adapter fallback
After=NetworkManager-wait-online.service dataark-portal-dns.service dataark-pass-through.service
Wants=NetworkManager-wait-online.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-wifi-roles --boot
TimeoutStartSec=240

[Install]
WantedBy=multi-user.target
'''

def main():
    if os.geteuid()!=0:
        raise SystemExit('Run as root on the Ark.')
    destination = Path('/usr/local/libexec')
    destination.mkdir(parents=True,exist_ok=True)
    for source,name in [('wifi_role_manager.py','dataark-wifi-roles'),('wifi_interfaces.py','wifi_interfaces.py')]:
        content=(ROOT/'tools'/source).read_bytes()
        compile(content,source,'exec')
        path=destination/name
        if path.is_symlink(): raise SystemExit('Refusing symlink: '+str(path))
        temp=path.with_name(path.name+'.new')
        temp.write_bytes(content);temp.chmod(0o755 if source.endswith('manager.py') else 0o644)
        os.chown(temp,0,0);os.replace(temp,path)
    if not Path('/usr/sbin/ethtool').is_file():
        raise SystemExit('Install ethtool before enabling adapter assignment.')
    # Publish the current assignment; installing never swaps radios.
    ap=subprocess.check_output(['nmcli','-g','connection.interface-name','connection','show','DataArk'],text=True).strip()
    upstream=next((p.name for p in sorted(Path('/sys/class/net').glob('wlan*')) if p.name!=ap),'')
    preference=Path('/etc/dataark/wifi-roles.json')
    if not preference.exists():
        address=subprocess.check_output(['/usr/sbin/ethtool','-P',ap],text=True).split()[-1].lower()
        import re
        if not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',address):raise SystemExit('Cannot identify current hotspot hardware.')
        preference.write_text(json.dumps({'schema':1,'hotspot_adapter':address,'fallback':'builtin'},indent=2)+'\n');preference.chmod(0o644)
    runtime=Path('/run/dataark-wifi-roles.json')
    runtime.write_text(json.dumps({'hotspot':ap,'upstream':upstream})+'\n');runtime.chmod(0o644)
    unit=Path('/etc/systemd/system/dataark-wifi-roles.service')
    unit.write_text(UNIT);unit.chmod(0o644)
    subprocess.run(['systemd-analyze','verify',str(unit)],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable',unit.name],check=True)
    print('Adapter selection installed; existing assignment retained. Boot fallback enabled.')

if __name__=='__main__': main()
