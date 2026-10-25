"""Read-only worker progress for the dashboard; no privileged operations."""
from datetime import datetime, timezone
import json
import re
from pathlib import Path

PATH = Path('/var/lib/dataark/updates/status.json')
LABELS = {'idle':'Idle', 'waiting':'Waiting to update', 'checking':'Checking updates',
    'downloading':'Downloading', 'verifying':'Verifying', 'activating':'Activating',
    'recovering':'Recovering', 'publishing':'Publishing', 'error':'Update failed'}


def worker_progress(path=None):
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

MAP_STATE=Path('/var/lib/dataark/maps/usa-expansion.json')
MAP_LOG=Path('/var/lib/dataark/maps/usa-expansion.log')
def map_progress(state_path=None,log_path=None,active=None):
    try:
        data=json.loads((state_path or MAP_STATE).read_text())
        state=data.get('state')
        if state not in ('downloading','verifying','verified','publishing','failed'):return None
        if active is None:
            unit='dataark-usa-map-publish.service' if state in ('verified','publishing') else 'dataark-usa-map-extract.service'
            events=Path('/sys/fs/cgroup/system.slice')/unit/'cgroup.events'
            active=events.is_file() and 'populated 1' in events.read_text()
        if state=='failed' or not active:
            return {'state':'error','asset':'U.S. offline map','label':'Map update needs attention','detail':data.get('error') or 'The map job is not running. The previous map remains available.'}
        if state in ('verifying','verified','publishing'):
            return {'state':'publishing' if state=='publishing' else 'verifying','asset':'U.S. offline map','label':'Publishing U.S. offline map' if state=='publishing' else 'Verifying U.S. offline map','detail':'The previous map remains available until activation completes.'}
        percent=0
        with (log_path or MAP_LOG).open('rb') as stream:
            stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-8192));tail=stream.read().decode(errors='replace')
        values=re.findall(r'fetching chunks\s+(\d+)%',tail)
        if values:percent=int(values[-1])
        return {'state':'downloading','asset':'U.S. offline map','percent':percent,'label':('Downloading '+str(percent)+'%: U.S. offline map') if percent else 'Preparing U.S. offline map','detail':'Staging all 50 states. The existing map remains available.'}
    except FileNotFoundError:return None
    except (OSError,ValueError,TypeError,AttributeError):return None

def progress(path=None):
    worker=worker_progress(path)
    if path is not None:return worker
    current=map_progress()
    if not current:return worker
    if worker and worker.get('state') not in (None,'idle','waiting','error'):
        return {**worker,'detail':(worker.get('detail','')+' | '+current['label']).strip(' |')}
    return current
