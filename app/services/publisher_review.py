"""Public status and fixed-scope privileged requests for publisher reviews."""
import hashlib
import json
from pathlib import Path
from app.services import reference_checks

ROOT = Path(__file__).resolve().parents[2]
STATE = Path('/var/lib/dataark/publisher-review')

def installation_step(phase):
    phase=(phase or '').lower()
    for prefix,step in [('checking installed',1),('checking candidate',2),('backing up',3),('retaining the previous',3),('installing verified',4),('publishing',5)]:
        if phase.startswith(prefix):return step
    return None


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
        if value.get('state') in ('installing','preparing') and not value.get('install_telemetry' if value.get('state')=='installing' else 'telemetry'):
            try:
                job=value.get('job','')
                if __import__('re').fullmatch(r'[a-f0-9]{32}',job):
                    observed=json.loads((STATE/'progress'/(job+'.json')).read_text())
                    if observed.get('job')==job and 0<=__import__('time').time()-observed.get('observed_at',0)<15:
                        value['install_telemetry' if value.get('state')=='installing' else 'telemetry']=observed['telemetry']
            except (OSError,ValueError,KeyError,TypeError):pass
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
        input=json.dumps({'action': 'publisher_review', **payload}), text=True, capture_output=True, timeout=120 if payload.get('action')=='source_settings' else 30)
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
            if state=='error' and not current.get('source_url'):
                from app.services.manifest import load_manifest
                asset=next((a for a in load_manifest(ROOT/'dataark.yaml')['assets'] if a['id']==current['asset_id']),None)
                if asset:current['source_url']=reference_checks.source(asset)
            if state=='error' and (reference_checks.source_policy(reference_checks.settings(),current.get('source_url'))!='active' or reference_checks.warning_snoozed(reference_checks.settings(),current.get('source_url'))):return None
            edition=current.get('candidate_edition') or (current.get('edition') or {}).get('edition')
            title=current['title']
            if edition:title=('U.S. street map' if current['asset_id']=='osm-massachusetts' else title)+' — candidate edition '+edition
            telemetry=current.get('install_telemetry') if current.get('state')=='installing' else current.get('telemetry')
            telemetry=telemetry or {}
            step=installation_step(telemetry.get('phase')) if current.get('state')=='installing' else telemetry.get('step')
            return {'state':state,'asset':title,'asset_id':current['asset_id'],'job':current['job'],
                    'source_url':current.get('source_url'),'review_failure':state=='error',
                    'units_processed':telemetry.get('units_processed'),'total_units':telemetry.get('total_units'),'unit':telemetry.get('unit'),
                    'percent':telemetry.get('percent'),'phase':telemetry.get('phase'),
                    'step':step,'total_steps':(5 if current.get('state')=='installing' else telemetry.get('total_steps')) if step else None,
                    'bytes_processed':telemetry.get('bytes_processed'),'total_bytes':telemetry.get('total_bytes'),
                    'records_processed':telemetry.get('records_processed'),
                    'estimated_remaining_seconds':telemetry.get('estimated_remaining_seconds'),
                    'label':{'waiting':'Publisher review','downloading':'Preparing publisher candidate','activating':'Applying publisher review','error':'Publisher review needs attention'}[state]+': '+title, 'detail':current.get('message','')}
    except (OSError,ValueError,KeyError,TypeError):return None
    return None
