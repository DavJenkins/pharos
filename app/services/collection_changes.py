"""Bounded, durable collection lifecycle feed for local Home Assistant polling.

Progress updates replace current activity; only phase changes become events.
No credentials, source URLs, caller addresses or configuration bodies are stored.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sqlite3
import uuid

STATE = Path('/var/lib/dataark/collection-changes')
KEEP = 1000
KINDS = {'suggested', 'approved', 'queued', 'request_started', 'downloading',
         'verifying', 'activating', 'publishing', 'installed', 'removed',
         'rejected', 'cancelled', 'failed', 'configuration_queued',
         'configuration_published', 'configuration_failed'}


@contextmanager
def database():
    if STATE.is_symlink() or (STATE/'changes.sqlite3').is_symlink():
        raise OSError('Collection journal cannot be a symlink')
    STATE.mkdir(parents=True, exist_ok=True)
    if os.name == 'posix':
        if os.geteuid() == 0:
            import pwd
            user = pwd.getpwnam('admin')
            os.chown(STATE, user.pw_uid, user.pw_gid)
        STATE.chmod(0o2770)
    path = STATE/'changes.sqlite3'
    db = sqlite3.connect(path, timeout=2)
    try:
        if os.name == 'posix':
            path.chmod(0o660)
            if os.geteuid() == 0:
                os.chown(path, user.pw_uid, user.pw_gid)
        db.row_factory = sqlite3.Row
        db.executescript('''CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS changes (sequence INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT);
            CREATE TABLE IF NOT EXISTS activity (key TEXT PRIMARY KEY, marker TEXT, payload TEXT);''')
        db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', ('journal_id', uuid.uuid4().hex))
        yield db
        db.commit()
    finally:
        db.close()


def text(value, maximum=160):
    return str(value or '')[:maximum]


def record(kind, *, collection_id='', title='', operation_id='', action='', error_type='', percent=None, activity_key=None):
    if kind not in KINDS and kind not in {'idle', 'waiting', 'checking', 'recovering'}:
        raise ValueError('Unknown collection lifecycle event')
    payload = {'kind':kind, 'collection_id':text(collection_id), 'title':text(title),
               'operation_id':text(operation_id), 'action':text(action),
               'timestamp':datetime.now(timezone.utc).isoformat(timespec='milliseconds')}
    if error_type:
        payload['error_type'] = text(error_type, 80)
    if type(percent) in (int, float) and math.isfinite(percent) and 0 <= percent <= 100:
        payload['percent'] = percent
    with database() as db:
        journal = db.execute("SELECT value FROM metadata WHERE key='journal_id'").fetchone()[0]
        should_emit = kind in KINDS
        if activity_key:
            marker = json.dumps([kind, payload['collection_id'], payload['title'], payload['operation_id']])
            prior = db.execute('SELECT marker,payload FROM activity WHERE key=?', (activity_key,)).fetchone()
            if kind == 'failed' and prior and not payload['title']:
                previous = json.loads(prior['payload'])
                payload['title'] = previous.get('title', '')
                payload['collection_id'] = previous.get('collection_id', '')
                marker = json.dumps([kind, payload['collection_id'], payload['title'], payload['operation_id']])
            should_emit = should_emit and (prior is None or prior[0] != marker)
            db.execute('INSERT OR REPLACE INTO activity VALUES (?,?,?)',
                       (activity_key, marker, json.dumps(payload)))
        if should_emit:
            payload['event_id'] = journal + ':' + uuid.uuid4().hex
            db.execute('INSERT INTO changes(payload) VALUES (?)', (json.dumps(payload),))
            db.execute('DELETE FROM changes WHERE sequence <= (SELECT coalesce(max(sequence),0)-? FROM changes)', (KEEP,))


def safe_record(kind, **fields):
    """Notification failures must not damage the collection transaction."""
    try:
        record(kind, **fields)
    except (OSError, sqlite3.Error, ValueError, KeyError):
        import logging
        logging.getLogger(__name__).warning('Collection notification could not be recorded')


def from_library(event, fields):
    identity = {target:fields.get(source, '') for target, source in
                [('collection_id','asset_id'), ('title','title'), ('operation_id','operation'),
                 ('action','action'), ('error_type','error_type')]}
    if event == 'update_progress':
        state = fields.get('phase')
        state = 'failed' if state == 'error' else state
        if state in KINDS | {'idle','waiting','checking','recovering'}:
            if state == 'failed' and not identity['error_type']:
                identity['error_type'] = 'UpdateError'
            safe_record(state, **identity, percent=fields.get('percent'), activity_key='updater')
    else:
        kind = {'operation_started':'request_started', 'operation_failed':'failed',
                'archive_activated':'installed', 'operation_completed':
                'removed' if fields.get('outcome') == 'removed' else 'configuration_published' if fields.get('outcome')=='configuration_published' else 'queued'}.get(event)
        if kind:
            if kind == 'queued' and identity['action'] in {'download', 'restore'}:
                safe_record('approved', **identity)
            safe_record(kind, **identity)


def snapshot(limit=200):
    limit = max(1, min(KEEP, limit))
    with database() as db:
        journal = db.execute("SELECT value FROM metadata WHERE key='journal_id'").fetchone()[0]
        rows = list(reversed(db.execute('SELECT sequence,payload FROM changes ORDER BY sequence DESC LIMIT ?', (limit,)).fetchall()))
        events = [dict(json.loads(row['payload']), sequence=row['sequence']) for row in rows]
        activity = {row['key']:json.loads(row['payload']) for row in db.execute('SELECT key,payload FROM activity')}
        return {'journal_id':journal, 'latest_sequence':events[-1]['sequence'] if events else 0,
                'oldest_sequence':events[0]['sequence'] if events else 0,
                'events':events, 'activity':activity, 'retention_events':KEEP}
