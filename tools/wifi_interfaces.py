"""Read the root-published role assignment; interface names are runtime details."""
import json
from pathlib import Path
import re
import subprocess
import time

RUNTIME = Path('/run/dataark-wifi-roles.json')
PLATFORM = Path('/etc/dataark/platform.json')


def platform_settings():
    invalid={'schema':1,'network_mode':'lan','roles':{},'configuration_error':True}
    try:
        if not PLATFORM.exists():return {}
        value=json.loads(PLATFORM.read_text())
        if not isinstance(value,dict) or value.get('schema')!=1:return invalid
        if value.get('network_mode')=='hotspot':return {}
        roles=value.get('roles',{})
        if value.get('network_mode')=='lan' and isinstance(roles,dict) and isinstance(roles.get('identities',{}),dict):
            if all(v is None or isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,14}',v) for k,v in roles.items() if k in {'ethernet','wifi','upstream','hotspot'}):
                return value
        return invalid
    except FileNotFoundError:return {}
    except (OSError,ValueError,TypeError):return invalid


def ethernet_interface():
    settings=platform_settings()
    return role_interface(settings,'ethernet') if settings else 'eth0'


def role_interface(settings,role):
    roles=settings.get('roles',{});name=roles.get(role) or ''
    identity=roles.get('identities',{}).get(role)
    if not identity:return name
    if not isinstance(identity,str) or not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',identity):return ''
    candidates=[name]+[p.name for p in sorted(Path('/sys/class/net').iterdir())[:64] if p.name!=name]
    deadline=time.monotonic()+1.5
    for candidate in candidates:
        remaining=deadline-time.monotonic()
        if remaining<=0:return ''
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,14}',candidate):continue
        try:
            result=subprocess.run(['ethtool','-P',candidate],capture_output=True,text=True,timeout=min(.3,remaining),check=False)
            if result.returncode==0 and result.stdout.strip().lower().endswith(identity):return candidate
        except (OSError,subprocess.SubprocessError):pass
    return ''

def interfaces():
    settings=platform_settings()
    if settings:return '',role_interface(settings,'wifi')
    try:
        value = json.loads(RUNTIME.read_text())
        ap, upstream = value['hotspot'], value['upstream']
        if (isinstance(ap, str) and isinstance(upstream, str)
                and re.fullmatch(r'wlan[0-9]+', ap)
                and (not upstream or re.fullmatch(r'wlan[0-9]+', upstream))
                and ap != upstream):
            return ap, upstream
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return 'wlan0', 'wlan1'
