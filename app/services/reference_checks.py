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
    if asset.get('source_check_url'):
        return asset['source_check_url']
    if asset['id'] == 'callbook-callsigns-sqlite':
        return 'https://data.fcc.gov/download/pub/uls/complete/l_amat.zip'
    if asset['id'] == 'osm-massachusetts':
        return read(ROOT / 'deploy/reference/osm-usa.json', {}).get('source')
    return asset.get('download_url')

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
    edition=record.get('edition_discovery',{})
    candidate=edition.get('candidate')
    attempt = record.get('attempted_at')
    def date(value):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc).isoformat(timespec='seconds') if value else None
        except (ValueError, TypeError, OverflowError, OSError):
            return None
    last = date(attempt)
    due = date(attempt + seconds) if last and seconds else None
    return {'policy': 'source_check', 'interval': interval, 'enabled': enabled,
            'last_checked': last, 'last_success': date(record.get('checked_at')),
            'next_due': due, 'due_now': enabled and (not last or attempt + seconds <= now),
            'history_available': not state.get('unreadable', False),
            'result': 'edition_available' if candidate else 'error' if edition.get('status')=='error' else record.get('status', 'awaiting'), 'detail': (edition.get('detail','')+' '+record.get('detail','')).strip() if candidate or edition.get('status')=='error' else record.get('detail', ''),
            'available_edition': candidate, 'edition_check': edition,
            'pending_change': bool(record.get('pending_change') or candidate), 'source_url': url,
            'pinned_version': asset.get('version_pin'),
            'scope': 'Checks recorded sources and configured edition families; new editions require review and earlier editions are retained.'}
