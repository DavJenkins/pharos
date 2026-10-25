"""Validate SQLite backups, then restore reviewed data using the live board schema."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from app.services import community as board

MAX_UPLOAD=128*1024*1024
BACKUPS=Path('/var/backups/dataark-community')
LOCK=threading.RLock()
TOKEN=re.compile(r'[A-Za-z0-9_-]{32}')
COLUMNS=('id','parent_id','category','title','name','body','created_at','delete_hash')

def folder():
    path=board.DATABASE.parent/'restores'
    if path.is_symlink():raise board.BoardError(503,'Restore staging needs caretaker attention.')
    path.mkdir(exist_ok=True,mode=0o700);path.chmod(0o700)
    return path

def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()

def cleanup():
    with LOCK:
        for file in folder().glob('*.json'):
            if not TOKEN.fullmatch(file.stem):continue
            if file.stat().st_mtime<time.time()-600:
                file.with_suffix('.sqlite3').unlink(missing_ok=True);file.unlink(missing_ok=True)

def fingerprint(db):
    value=hashlib.sha256()
    for row in db.execute('SELECT '+','.join(COLUMNS)+' FROM messages ORDER BY id'):
        value.update(json.dumps(tuple(row),ensure_ascii=False,separators=(',',':')).encode())
    for row in db.execute("SELECT key,value FROM metadata WHERE key GLOB 'edited:*' ORDER BY key"):
        value.update(json.dumps(tuple(row),ensure_ascii=False).encode())
    row=db.execute("SELECT value FROM metadata WHERE key='notice'").fetchone()
    value.update((row[0] if row else '').encode())
    return value.hexdigest()

def summary(db):
    counts=db.execute('SELECT sum(parent_id IS NULL),sum(parent_id IS NOT NULL),min(created_at),max(created_at) FROM messages').fetchone()
    row=db.execute("SELECT value FROM metadata WHERE key='notice'").fetchone()
    notice=json.loads(row[0]) if row else {'text':'','color':'#fff0bd'}
    return {'posts':counts[0] or 0,'replies':counts[1] or 0,'oldest':counts[2],'newest':counts[3],
            'banner':notice.get('text',''),'color':notice.get('color','#fff0bd')}

def timestamp(value):
    if not isinstance(value,str) or len(value)>40:raise ValueError('Invalid message date.')
    if datetime.fromisoformat(value).tzinfo is None:raise ValueError('Message date has no timezone.')
    return value

def normalize(source,destination):
    """Read untrusted SQLite as data only; never import its SQL/schema/triggers."""
    policy=board.settings()
    with Path(source).open('rb') as stream:
        if stream.read(16)!=b'SQLite format 3\x00':raise ValueError('Choose a SQLite community-board backup.')
    if Path(source).stat().st_size>MAX_UPLOAD:raise ValueError('Backup exceeds 128 MiB.')
    with closing(sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as old:
        old.row_factory=sqlite3.Row;old.enable_load_extension(False)
        old.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1024*1024)
        old.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,65536)
        old.setlimit(sqlite3.SQLITE_LIMIT_COLUMN,64)
        old.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED,0)
        old.execute('PRAGMA trusted_schema=OFF');old.execute('PRAGMA query_only=ON')
        deadline=time.monotonic()+20
        old.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        if old.execute('PRAGMA user_version').fetchone()[0]!=1:raise ValueError('Unsupported board-backup version.')
        for row in old.execute('SELECT type,name,tbl_name,sql FROM sqlite_master'):
            if row['type'] in ('trigger','view') or (row['type']=='table' and row['name'] not in ('messages','metadata','limits','sqlite_sequence')):
                raise ValueError('Unexpected database objects; this is not a supported board backup.')
        for table,names in [('messages',COLUMNS),('metadata',('key','value'))]:
            columns=old.execute('PRAGMA table_xinfo('+table+')').fetchall()
            if tuple(row['name'] for row in columns)!=names or any(row['hidden'] for row in columns):
                raise ValueError('Backup does not have the expected board columns.')
        columns=old.execute('PRAGMA table_xinfo(messages)').fetchall()
        if columns[0]['type'].upper()!='INTEGER' or columns[0]['pk']!=1:raise ValueError('Unsupported message identifiers.')
        if old.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Backup failed its database integrity check.')
        count=old.execute('SELECT count(*) FROM messages').fetchone()[0]
        if count>min(5000,policy['max_messages']):raise ValueError('Backup exceeds the configured board capacity.')
        fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        with closing(sqlite3.connect(destination)) as new:
            new.executescript('CREATE TABLE messages(id INTEGER PRIMARY KEY,parent_id INTEGER,category TEXT,title TEXT,name TEXT,body TEXT,created_at TEXT,delete_hash TEXT); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); PRAGMA user_version=1;')
            roots={};reply_counts={}
            for row in old.execute('SELECT '+','.join(COLUMNS)+' FROM messages ORDER BY id'):
                identifier,parent=row['id'],row['parent_id']
                if type(identifier)!=int or not 1<=identifier<=2147483647:raise ValueError('Invalid message identifier.')
                if row['category'] not in policy['categories']:raise ValueError('A backup category is not in this Ark’s configuration.')
                values=[identifier,parent,row['category'],board.clean(row['title'],'Title',120,parent is None),
                        board.clean(row['name'],'Display name',40),board.clean(row['body'],'Message',min(4000,policy['body_characters'])),timestamp(row['created_at'])]
                if not isinstance(row['delete_hash'],str) or not re.fullmatch('[0-9a-fA-F]{64}',row['delete_hash']):raise ValueError('Invalid author deletion-code hash.')
                values.append(row['delete_hash'].lower())
                if parent is None:roots[identifier]=row['category']
                else:
                    if type(parent)!=int or parent not in roots or roots[parent]!=row['category'] or row['title']!='':raise ValueError('A reply has an invalid parent conversation.')
                    reply_counts[parent]=reply_counts.get(parent,0)+1
                    if reply_counts[parent]>min(200,policy['max_replies']):raise ValueError('A conversation exceeds the reply limit.')
                new.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)',values)
            notice=old.execute("SELECT value FROM metadata WHERE key='notice'").fetchone()
            if notice:
                value=json.loads(notice[0])
                if not isinstance(value,dict):raise ValueError('Invalid banner record.')
                value={'text':board.clean(value.get('text'),'Banner',300,False),**board.notice_appearance(value,legacy=True),'updated_at':value.get('updated_at')}
                if not isinstance(value['color'],str) or not re.fullmatch('#[0-9a-fA-F]{6}',value['color']):raise ValueError('Invalid banner color.')
                if value['updated_at'] is not None:timestamp(value['updated_at'])
                new.execute('INSERT INTO metadata VALUES (?,?)',('notice',json.dumps(value)))
            for record in old.execute("SELECT key,value FROM metadata WHERE key GLOB 'edited:*'"):
                if not re.fullmatch(r'edited:[1-9][0-9]{0,9}',record['key']):raise ValueError('Invalid edit marker identifier.')
                identifier=int(record['key'].split(':')[1])
                if not new.execute('SELECT 1 FROM messages WHERE id=?',(identifier,)).fetchone():raise ValueError('Edit marker refers to a missing message.')
                marker=json.loads(record['value'])
                if not isinstance(marker,dict) or set(marker)!={'edited_at','revisions'}:raise ValueError('Invalid edit marker.')
                timestamp(marker['edited_at'])
                if type(marker['revisions'])!=int or not 1<=marker['revisions']<=2147483647:raise ValueError('Invalid edit revision count.')
                new.execute('INSERT INTO metadata VALUES (?,?)',(record['key'],json.dumps(marker)))
            new.commit()
            return summary(new)

def prepare(source,peer):
    with LOCK:
        cleanup();token=secrets.token_urlsafe(24);target=folder()/(token+'.sqlite3');meta=target.with_suffix('.json')
        try:
            backup=normalize(source,target)
            with board.connect() as live:
                live.execute('BEGIN')
                record={'expires':time.time()+600,'peer':board.peer_key(live,peer),'fingerprint':fingerprint(live),
                        'sha256':digest(target),'backup':backup,'current':summary(live)}
            # One pending review per device; another review explicitly supersedes it.
            for other in folder().glob('*.json'):
                if not TOKEN.fullmatch(other.stem):continue
                if json.loads(other.read_text()).get('peer')==record['peer']:
                    other.with_suffix('.sqlite3').unlink(missing_ok=True);other.unlink(missing_ok=True)
            if len(list(folder().glob('*.json')))>=3:raise board.BoardError(429,'Three backups are already awaiting review. Try again in ten minutes.')
            fd=os.open(meta,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w') as stream:json.dump(record,stream)
            return {'token':token,'backup':backup,'current':record['current'],'expires_in':600}
        except Exception as error:
            target.unlink(missing_ok=True);meta.unlink(missing_ok=True)
            if isinstance(error,board.BoardError):raise
            if isinstance(error,(sqlite3.Error,ValueError,KeyError,TypeError,OverflowError)):
                raise board.BoardError(400,'Backup validation failed: '+str(error)[:240]) from None
            raise board.BoardError(503,'Unable to stage the backup. Check private storage space and permissions.') from None

def apply(token,peer):
    if not isinstance(token,str) or not TOKEN.fullmatch(token):raise board.BoardError(400,'Validate a backup first.')
    with LOCK:
        meta=folder()/(token+'.json');source=meta.with_suffix('.sqlite3')
        if not meta.is_file() or meta.is_symlink() or source.is_symlink():raise board.BoardError(410,'The backup preview expired. Validate the file again.')
        record=json.loads(meta.read_text())
        if record['expires']<time.time():
            source.unlink(missing_ok=True);meta.unlink(missing_ok=True)
            raise board.BoardError(410,'The backup preview expired. Validate the file again.')
        if not source.is_file() or digest(source)!=record['sha256']:raise board.BoardError(409,'The reviewed backup changed. Validate it again.')
        try:
            with board.connect() as live:
                live.execute('BEGIN IMMEDIATE')
                if not hmac.compare_digest(record['peer'],board.peer_key(live,peer)):raise board.BoardError(403,'Validate the backup from this device first.')
                if fingerprint(live)!=record['fingerprint']:raise board.BoardError(409,'The board changed after the preview. Validate again before replacing it.')
                policy=board.settings()
                if record['backup']['posts']+record['backup']['replies']>min(5000,policy['max_messages']):raise board.BoardError(409,'Board capacity changed. Validate the backup again.')
                safety=BACKUPS/('before-restore-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+secrets.token_hex(4)+'.sqlite3')
                # Another read connection can snapshot the committed WAL state while this
                # write reservation prevents intervening posts, deletions or banner edits.
                board.snapshot(safety)
                with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as staged:
                    live.execute("DELETE FROM metadata WHERE key GLOB 'edited:*'")
                    live.execute('DELETE FROM messages')
                    for row in staged.execute('SELECT '+','.join(COLUMNS)+' FROM messages ORDER BY id'):
                        live.execute('INSERT INTO messages('+','.join(COLUMNS)+') VALUES (?,?,?,?,?,?,?,?)',row)
                    for marker in staged.execute("SELECT key,value FROM metadata WHERE key GLOB 'edited:*'"):
                        live.execute('INSERT INTO metadata VALUES (?,?)',marker)
                    notice=staged.execute("SELECT value FROM metadata WHERE key='notice'").fetchone()
                    live.execute("DELETE FROM metadata WHERE key='notice'")
                    if notice:live.execute('INSERT INTO metadata VALUES (?,?)',('notice',notice[0]))
                # The live rate-limit salt and counters are deliberately not rolled back.
        except board.BoardError:raise
        except (OSError,sqlite3.Error):raise board.BoardError(503,'Restore could not complete. The transaction was rolled back; check private storage and try again.') from None
        result={'restored':True,'backup':record['backup'],'safety_backup':safety.name}
        try:
            source.unlink(missing_ok=True);meta.unlink(missing_ok=True)
            for old in sorted(BACKUPS.glob('before-restore-*.sqlite3'),key=lambda p:p.stat().st_mtime_ns,reverse=True)[3:]:
                if old.is_file() and not old.is_symlink():old.unlink()
        except OSError:result['warning']='Restored successfully, but staging/old snapshot cleanup needs caretaker attention.'
        return result
