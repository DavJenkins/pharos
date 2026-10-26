"""Public, bounded appliance health for automation; never exposes credentials."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from app.services.https_setup import public_status
from app.services.status_service import get_status

REFERENCE = Path('/var/lib/dataark/reference-checks/state.json')

def failed_units():
    result = subprocess.run(['systemctl', '--failed', '--no-legend', '--plain', '--no-pager'],
                            capture_output=True, text=True, timeout=3, check=False)
    if result.returncode:
        raise OSError('Service health query failed')
    return sorted({line.split()[0] for line in result.stdout.splitlines() if line.strip()})

def collect():
    status = get_status()
    problems = []
    def add(code, severity, message):
        problems.append({'id':code, 'severity':severity, 'message':message})
    for issue in status['status']['issues']:
        add('system.' + hashlib.sha256(issue.encode()).hexdigest()[:12],
            'error' if status['status']['state'] == 'error' else 'warning', issue)
    update = status['status'].get('update') or {}
    if update.get('state') == 'error':
        add('content.update_failed', 'error', update.get('label', 'Content update failed'))
    certificate = public_status()
    health = certificate.get('certificate_health')
    if health in ('expired', 'renewal_due', 'unknown'):
        add('https.certificate', 'error' if health == 'expired' else 'warning',
            'HTTPS certificate ' + health.replace('_', ' '))
    if certificate.get('phase') == 'failed':
        add('https.setup_failed', 'warning', 'Optional HTTPS setup needs attention')
    try:
        for unit in failed_units():
            add('service.' + unit, 'error', 'Failed service: ' + unit)
    except (OSError, subprocess.TimeoutExpired):
        add('services.telemetry', 'warning', 'Failed-service telemetry unavailable')
    reference = {'available':False}
    try:
        entries = json.loads(REFERENCE.read_text())['sources'].values()
        entries = list(entries)
        errors = sum(v.get('status') == 'error' for v in entries)
        changed = sum(bool(v.get('pending_change')) for v in entries)
        reference = {'available':True, 'checked_sources':len(entries), 'errors':errors, 'changed':changed}
        if errors: add('content.source_checks', 'warning', f'{errors} publisher checks need attention; saved content is retained')
        if changed: add('content.source_changes', 'warning', f'{changed} publisher changes await review')
    except FileNotFoundError:
        pass  # Not configured on every Ark.
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        add('content.check_telemetry', 'warning', 'Publisher-check telemetry unavailable')
    problems.sort(key=lambda value:value['id'])
    fingerprint = hashlib.sha256(json.dumps(problems, sort_keys=True).encode()).hexdigest()[:24]
    return {'schema_version':1, 'state':'error' if any(p['severity']=='error' for p in problems) else 'warning' if problems else 'ok',
            'problem_count':len(problems), 'fingerprint':fingerprint, 'problems':problems,
            'certificate':certificate, 'source_checks':reference,
            'services':status['services'], 'update':update,
            'observed_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
