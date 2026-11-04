"""Public status and fixed-scope privileged requests for publisher reviews."""
import hashlib
import json
from pathlib import Path
from app.services import reference_checks

ROOT = Path(__file__).resolve().parents[2]
STATE = Path('/var/lib/dataark/publisher-review')


def revision(record):
    discovery=record.get('edition_discovery') or {}
    identity={k:record.get(k) for k in ('fingerprint','pending_change','status')}
    identity['edition_discovery']={k:discovery.get(k) for k in
        ('status','candidate','current_edition','reviewed_candidate')}
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def status(asset_id):
    if not isinstance(asset_id, str) or not __import__('re').fullmatch(r'[a-zA-Z0-9_-]{1,160}', asset_id):
        raise ValueError('Invalid collection identifier')
    path = STATE / (asset_id + '.json')
    try:
        value = json.loads(path.read_text())
        if value.get('state') in ('queued', 'preparing', 'installing') and __import__('time').time() - value.get('updated_at', 0) > 15:
            import subprocess
            if subprocess.run(['systemctl', 'is-active', '--quiet', 'dataark-publisher-review-' + value['job']], capture_output=True).returncode:
                value.update(state='interrupted', message='Review interrupted. Prepare again to recover and retry; saved copies are retained.')
        return value
    except FileNotFoundError:
        return {'state': 'idle'}


def invoke(payload):
    import subprocess
    result = subprocess.run(['/usr/bin/sudo', '-n', '--', '/usr/local/libexec/dataark-library'],
        input=json.dumps({'action': 'publisher_review', **payload}), text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stdout.strip() or 'Publisher review helper unavailable')
    return json.loads(result.stdout)


def active_progress():
    try:
        records=[json.loads(path.read_text()) for path in STATE.glob('*.json')]
        if not records:return None
        latest=max(records,key=lambda v:v.get('updated_at',0))
        current=status(latest['asset_id'])
        state={'queued':'waiting','preparing':'downloading','installing':'activating','ready':'waiting','failed':'error','interrupted':'error'}.get(current.get('state'))
        if state:
            edition=current.get('candidate_edition') or (current.get('edition') or {}).get('edition')
            title=current['title']
            if edition:title=('U.S. street map' if current['asset_id']=='osm-massachusetts' else title)+' — candidate edition '+edition
            return {'state':state,'asset':title, 'label':{'waiting':'Publisher review','downloading':'Preparing publisher candidate','activating':'Applying publisher review','error':'Publisher review needs attention'}[state]+': '+title, 'detail':current.get('message','')}
    except (OSError,ValueError,KeyError,TypeError):return None
    return None
