"""Bounded wired-adapter discovery shared by status and the privileged helper."""
import json
from pathlib import Path
import re
import subprocess

NET=Path('/sys/class/net')
NAME=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,14}')


def dependencies(interface):
    result=set();pending=[interface]
    while pending and len(result)<64:
        name=pending.pop()
        if not isinstance(name,str) or not NAME.fullmatch(name) or name in result:continue
        result.add(name);path=NET/name
        try:
            pending.extend(p.name.removeprefix('lower_') for p in path.glob('lower_*'))
            bridge=path/'brif'
            if bridge.is_dir():pending.extend(p.name for p in bridge.iterdir())
        except OSError:pass
    return result


def devices():
    result=[]
    try:
        for path in sorted(NET.iterdir())[:64]:
            try:
                if NAME.fullmatch(path.name) and (path/'device').exists() and not (path/'wireless').exists() and (path/'type').read_text().strip()=='1':
                    result.append(path.name)
            except OSError:continue  # A removed adapter must not hide the remaining ports.
    except OSError:pass
    physical=set(result)
    try:result.extend(p.name for p in sorted(NET.iterdir())[:64] if NAME.fullmatch(p.name) and dependencies(p.name)&physical)
    except OSError:pass
    # Preserve explicitly configured logical wired interfaces (bridge/bond/VLAN).
    try:
        config=json.loads(Path('/etc/dataark/platform.json').read_text())
        names=config.get('roles',{}).get('ethernets',[])
        names += [config.get('roles',{}).get('ethernet')]
        result.extend(name for name in names if isinstance(name,str) and NAME.fullmatch(name) and (NET/name).exists())
    except (OSError,ValueError,TypeError,AttributeError):pass
    return sorted(set(result))


def permanent_mac(interface):
    if not isinstance(interface,str) or not NAME.fullmatch(interface):return None
    try:
        result=subprocess.run(['/usr/sbin/ethtool','-P',interface],capture_output=True,text=True,timeout=2,check=False)
        mac=result.stdout.split()[-1].lower() if result.returncode==0 else ''
        return mac if re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',mac) and mac!='00:00:00:00:00:00' else None
    except (OSError,subprocess.SubprocessError,IndexError):return None
