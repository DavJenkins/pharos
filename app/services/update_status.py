"""Read-only worker progress for the dashboard; no privileged operations."""
from datetime import datetime, timezone
import json
from pathlib import Path

PATH = Path('/var/lib/dataark/updates/status.json')
LABELS = {'idle':'Idle', 'waiting':'Waiting to update', 'checking':'Checking updates',
    'downloading':'Downloading', 'verifying':'Verifying', 'activating':'Activating',
    'recovering':'Recovering', 'publishing':'Publishing', 'error':'Update failed'}


def progress(path=None):
    try:
        data = json.loads((path or PATH).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('state') not in LABELS:
            return {'label':'Update status unavailable'}
        updated = datetime.fromisoformat(data['updated'])
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        if data['state'] not in ('idle','waiting','error') and age > 180:
            return {**data, 'label':'Update status stale'}
        label = LABELS[data['state']]
        # Keep progress ahead of long archive titles so compact panels show it.
        percent = data.get('percent')
        if type(percent) in (int, float) and 0 <= percent <= 100:
            label += f' {percent:.0f}%'
        if data.get('asset') and data['state'] not in ('idle', 'waiting', 'error'):
            label += ': ' + str(data['asset'])
        return {**data, 'label':label}
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError):
        return {'label':'Update status unavailable'}