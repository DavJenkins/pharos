"""Public, bounded appliance health for automation; never exposes credentials."""
import hashlib
import json
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.services.https_setup import public_status
from app.services.status_service import get_status
from app.services import browser_reviews

REFERENCE = Path('/var/lib/dataark/reference-checks/state.json')

def failed_units():
    result = subprocess.run(['systemctl', '--failed', '--no-legend', '--plain', '--no-pager'],
                            capture_output=True, text=True, timeout=3, check=False)
    if result.returncode:
        raise OSError('Service health query failed')
    return sorted({line.split()[0] for line in result.stdout.splitlines() if line.strip()})

def collect(status=None):
    status = status if status is not None else get_status()
    problems = []
    def add(code, severity, message):
        problems.append({'id':code, 'severity':severity, 'message':message})
    for issue in status['status']['issues']:
        add('system.' + hashlib.sha256(issue.encode()).hexdigest()[:12],
            'error' if status['status']['state'] == 'error' else 'warning', issue)
    update = status['status'].get('update') or {}
    review_problem = None
    if update.get('state') == 'error':
        if update.get('review_failure'):
            review_problem={'id':'content.publisher_review','severity':'error','message':update.get('label','Publisher review needs attention')}
        else:
            add('content.update_failed', 'error', update.get('label', 'Content update failed'))
    from app.services.software_installation import status as software_status
    software=software_status()
    if software.get('state') in ('rolling_back','rollback_pending_health','rolled_back','refused'):
        add('software.update', 'warning', 'Software update: '+software['state'].replace('_',' '))
    certificate = public_status()
    health = certificate.get('certificate_health')
    if health in ('expired', 'renewal_due', 'unknown'):
        add('https.certificate', 'error' if health == 'expired' else 'warning',
            'HTTPS certificate ' + health.replace('_', ' '))
    if certificate.get('phase') == 'failed':
        add('https.setup_failed', 'warning', 'Optional HTTPS setup needs attention')
    try:
        for unit in failed_units():
            kind='login session' if unit.startswith('session-') and unit.endswith('.scope') else 'user manager' if unit.startswith('user@') else 'service'
            add('service.' + unit, 'error', 'Failed '+kind+': ' + unit)
    except (OSError, subprocess.TimeoutExpired):
        add('services.telemetry', 'warning', 'Failed-service telemetry unavailable')
    reference = {'available':False}
    try:
        from app.services.reference_checks import settings,source_policy,warning_snoozed
        config=settings()
        sources = {url:record for url,record in json.loads(REFERENCE.read_text())['sources'].items() if source_policy(config,url)=='active' and not warning_snoozed(config,url)}
        entries = list(sources.values())
        reviews = browser_reviews.snapshot()
        manual_urls = {r['source_url'] for r in reviews['reviews']}
        blocked = sum(url in manual_urls and browser_reviews.known_block(v) for url,v in sources.items())
        errors = sum(v.get('status') == 'error' for v in entries) - blocked
        changed = sum(bool(v.get('pending_change') or v.get('edition_discovery',{}).get('candidate')) for v in entries)
        reference = {'available':True, 'checked_sources':len(entries), 'errors':errors, 'changed':changed,
                     'blocked_automated_checks':blocked, 'browser_review':reviews}
        covered_review = review_problem and sources.get(update.get('source_url'),{}).get('status')=='error'
        if errors: add('content.source_checks', 'error' if covered_review else 'warning', f'{errors} publisher checks need attention; saved content is retained')
        if covered_review: review_problem=None
        if changed: add('content.source_changes', 'warning', f'{changed} publisher changes await review')
        if reviews['overdue']: add('content.browser_reviews', 'warning', f"{reviews['overdue']} browser reviews due; saved content is retained")
    except FileNotFoundError:
        pass  # Not configured on every Ark.
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        add('content.check_telemetry', 'warning', 'Publisher-check telemetry unavailable')
    from app.services import setup_security
    try:
        security=setup_security.snapshot()
        if security['unacknowledged']:add('security.first_owner_setup','warning',str(security['unacknowledged'])+' failed setup-code attempts need review')
    except (OSError,ValueError,RuntimeError,sqlite3.Error):
        add('security.telemetry','warning','Setup-security reporting needs attention')
    if review_problem: problems.append(review_problem)
    problems.sort(key=lambda value:value['id'])
    fingerprint = hashlib.sha256(json.dumps({'problems':problems,'source_checks':reference,'software':{key:software.get(key) for key in ('state','revision','sequence','operation_id')}}, sort_keys=True).encode()).hexdigest()[:24]
    return {'schema_version':1, 'state':'error' if any(p['severity']=='error' for p in problems) else 'warning' if problems else 'ok',
            'problem_count':len(problems), 'fingerprint':fingerprint, 'problems':problems,
            'certificate':certificate, 'source_checks':reference,
            'services':status['services'], 'update':update, 'software_update':software,
            'observed_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
