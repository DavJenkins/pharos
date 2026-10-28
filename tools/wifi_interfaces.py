"""Read the root-published role assignment; interface names are runtime details."""
import json
from pathlib import Path
import re

RUNTIME = Path('/run/dataark-wifi-roles.json')

def interfaces():
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
