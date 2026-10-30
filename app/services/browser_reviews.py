"""Read-only browser review schedules for explicitly configured public references."""
import json
import time
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'deploy/reference/browser-capture-policy.json'
MOUNT = Path('/mnt/storage')
CAPTURES = MOUNT / 'browser-capture-status.json'
REFERENCE = Path('/var/lib/dataark/reference-checks/state.json')


def read(path, fallback):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return fallback


def review(record, check, days, now=None):
    now = now or datetime.now(timezone.utc)
    verified = record.get('acquisition', {}).get('verified_at', record.get('checked_at'))
    # A successful automatic comparison also establishes a current baseline.
    if check.get('installed_sha256') == record.get('sha256') and check.get('state') == 'current':
        verified = check.get('checked_at') or verified
    try:
        stamp = datetime.fromisoformat(verified.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Review timestamp needs timezone')
        due = stamp + timedelta(days=days)
    except (ValueError, TypeError, AttributeError):
        verified, due = None, None
    changed = check.get('installed_sha256') == record.get('sha256') and check.get('state') == 'changed'
    return {'last_verified': verified, 'next_due': due.isoformat() if due else None,
            'review_interval_days': days, 'review_due': changed or due is None or now >= due,
            'changed': changed}


def snapshot(now=None):
    policy = read(POLICY, {})
    checks = read(CAPTURES, {})
    sources = read(REFERENCE, {}).get('sources', {})
    records = []
    for folder in policy.get('collections', []):
        for record in read(MOUNT / folder / 'sources.json', []):
            if record.get('id') not in policy.get('review_intervals_days', {}):
                continue
            if record.get('status') != 'installed' or not record.get('acquisition'):
                continue
            if not (MOUNT / folder / record['filename']).is_file():
                continue
            publisher = sources.get(record['url'], {})
            if publisher.get('status') in ('unchanged', 'baseline', 'changed', 'reachable'):
                continue  # Automatic access has recovered; normal source status applies.
            days = policy['review_intervals_days'][record['id']]
            if type(days) is not int or not 1 <= days <= 3650:
                raise ValueError('Invalid browser review interval')
            records.append({'id': record['id'], 'title': record['title'], 'source_url': record['url'],
                            **review(record, checks.get(record['id'], {}), days, now)})
    records.sort(key=lambda x: x['id'])
    return {'required': len(records), 'overdue': sum(x['review_due'] for x in records),
            'changed': sum(x['changed'] for x in records), 'reviews': records,
            'review_url': '/capture.html'}


def known_block(record):
    return record.get('status') == 'error' and 'HTTP 403' in record.get('detail', '')


@lru_cache(maxsize=2)
def _cached_snapshot(bucket):
    return snapshot()


def cached_snapshot():
    return _cached_snapshot(int(time.monotonic() // 10))
