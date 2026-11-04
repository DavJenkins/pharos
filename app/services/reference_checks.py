"""Read-only schedule and result projection for non-Kiwix publisher checks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'deploy/reference/reference-checks.json'
STATE = Path('/var/lib/dataark/reference-checks/state.json')

def read(path, fallback):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else fallback
    except (OSError, ValueError):
        return fallback

def settings():
    return read(CONFIG, {'enabled': False, 'interval': '7d'})

def source(asset):
    if asset.get('update_source', {}).get('kind') == 'kiwix_zim':
        return None
    override=settings().get('source_overrides',{}).get(asset['id'])
    if override:return override
    if asset.get('source_check_url'):
        return asset['source_check_url']
    if asset['id'] == 'callbook-callsigns-sqlite':
        return 'https://data.fcc.gov/download/pub/uls/complete/l_amat.zip'
    if asset['id'] == 'osm-massachusetts':
        return read(ROOT / 'deploy/reference/osm-usa.json', {}).get('source')
    return asset.get('download_url')

def source_policy(config, url):
    return config.get('source_policies',{}).get(url,{}).get('state','active')


def warning_snoozed(config,url,now=None):
    import time
    try:return float(config.get('source_policies',{}).get(url,{}).get('snoozed_until',0)) > (time.time() if now is None else now)
    except (TypeError,ValueError):return False


def retry_seconds(config, record):
    from tools.update_worker import interval_seconds
    base=interval_seconds(config.get('interval','7d'))
    failures=max(0,int(record.get('consecutive_failures',0)))
    return min(max(base,30*86400),base*2**min(max(0,failures-1),5))


def projection(asset, repository, config, state, now):
    from tools.update_worker import interval_seconds
    from datetime import datetime, timezone
    if asset.get('update_source', {}).get('kind') == 'kiwix_zim':
        return None
    if asset.get('removed'):
        return {'summary': 'Removed from the Ark · Checks paused', 'enabled': False}
    url = source(asset)
    if not url:
        return {'summary': 'Generated locally · Rebuilt with its collection', 'enabled': False}
    interval = config.get('interval', '7d')
    seconds = interval_seconds(interval)
    enabled = bool(config.get('enabled') and repository.get('enabled', True) and seconds)
    record = state.get('sources', {}).get(url, {})
    policy_state=source_policy(config,url)
    enabled=enabled and policy_state=='active'
    seconds=retry_seconds(config,record)
    edition=record.get('edition_discovery',{})
    candidate=edition.get('candidate')
    attempt = record.get('attempted_at')
    def date(value):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc).isoformat(timespec='seconds') if value else None
        except (ValueError, TypeError, OverflowError, OSError):
            return None
    last = date(attempt)
    due = date(attempt + seconds) if enabled and last and seconds else None
    from app.services import browser_reviews
    manual = next((r for r in browser_reviews.cached_snapshot()['reviews'] if r['source_url'] == url), None)
    manual = manual if manual and browser_reviews.known_block(record) else None
    return {'policy': 'source_check', 'interval': interval, 'enabled': enabled,
            'warning_snoozed':warning_snoozed(config,url,now), 'warning_snoozed_until':date(config.get('source_policies',{}).get(url,{}).get('snoozed_until')), 'source_state':policy_state, 'consecutive_failures':record.get('consecutive_failures',0), 'browser_review': manual,
            'last_checked': last, 'last_success': date(record.get('checked_at')),
            'next_due': due, 'due_now': enabled and (not last or attempt + seconds <= now),
            'history_available': not state.get('unreadable', False),
            'result': policy_state if policy_state!='active' else 'edition_available' if candidate else 'error' if edition.get('status')=='error' else ('browser_review_due' if manual['review_due'] else 'browser_review_scheduled') if manual else record.get('status', 'awaiting'), 'detail': ('Publisher checks '+policy_state+' by the caretaker. Installed copy retained; freshness is not established.') if policy_state!='active' else (edition.get('detail','')+' '+record.get('detail','')).strip() if candidate or edition.get('status')=='error' else ('Browser review due. Saved copy remains available.' if manual['review_due'] else 'Verified offline copy retained; browser review scheduled.') if manual else ('Publisher unavailable; saved copy available. '+record.get('detail','')) if record.get('status')=='error' else record.get('detail', ''),
            'available_edition': candidate, 'edition_check': edition,
            'pending_change': policy_state=='active' and bool(record.get('pending_change') or candidate), 'source_url': url,
            'pinned_version': asset.get('version_pin'),
            'scope': 'Checks recorded sources and configured edition families; new editions require review and earlier editions are retained.'}
