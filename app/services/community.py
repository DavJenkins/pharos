"""Small offline board. SQLite stays on the system disk, outside public shares."""
import hashlib
from contextlib import contextmanager
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime, timezone
import time

ROOT = Path(__file__).resolve().parents[2]
DATABASE = Path('/var/lib/dataark/community/board.sqlite3')
CONFIG = ROOT / 'config/community.json'

class BoardError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)

def settings():
    value = json.loads(CONFIG.read_text())
    if value.get('schema') != 1 or not isinstance(value.get('categories'), dict):
        raise BoardError(503, 'Board configuration needs attention from the caretaker.')
    if not value.get('enabled'):
        raise BoardError(503, 'The community board is temporarily closed.')
    return value

@contextmanager
def connect():
    if not DATABASE.parent.is_dir():
        raise BoardError(503, 'Community board storage is not installed.')
    db = sqlite3.connect(DATABASE, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          parent_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
          category TEXT NOT NULL, title TEXT NOT NULL, name TEXT NOT NULL,
          body TEXT NOT NULL, created_at TEXT NOT NULL, delete_hash TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS messages_parent ON messages(parent_id,id);
        CREATE TABLE IF NOT EXISTS limits (peer TEXT NOT NULL, kind TEXT NOT NULL, moment REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS limits_time ON limits(moment);
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', ('peer_salt', secrets.token_hex(32)))
        db.execute('PRAGMA user_version=1')
    DATABASE.chmod(0o600)

def peer_key(db, peer):
    salt = db.execute('SELECT value FROM metadata WHERE key=?', ('peer_salt',)).fetchone()[0]
    return hmac.new(bytes.fromhex(salt), peer.encode(), hashlib.sha256).hexdigest()

def limit(db, peer, kind, maximum, global_maximum=None):
    now = time.time()
    db.execute('DELETE FROM limits WHERE moment<?', (now-60,))
    key = peer_key(db, peer)
    count = db.execute('SELECT count(*) FROM limits WHERE peer=? AND kind=?', (key,kind)).fetchone()[0]
    total = db.execute('SELECT count(*) FROM limits WHERE kind=?', (kind,)).fetchone()[0]
    if count >= maximum or (global_maximum is not None and total >= global_maximum):
        raise BoardError(429, 'Too many attempts. Please wait a minute and try again.')
    db.execute('INSERT INTO limits VALUES (?,?,?)', (key,kind,now))

def auth_attempt(peer):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        limit(db, peer, 'authentication', 5)

def clean(value, label, maximum, required=True):
    if not isinstance(value, str):
        raise BoardError(400, label+' must be text.')
    value = value.strip()
    if (required and not value) or len(value) > maximum or any((ord(c)<32 and c not in '\n\t\r') or 0xD800<=ord(c)<=0xDFFF for c in value):
        raise BoardError(400, label+' must contain '+('1–' if required else 'at most ')+str(maximum)+' characters.')
    return value

def public(row):
    return {key:row[key] for key in ('id','parent_id','category','title','name','body','created_at')}

def listing(category='', offset=0):
    config = settings()
    if category and category not in config['categories']:
        raise BoardError(400, 'Unknown category.')
    if not 0 <= offset <= 5000:
        raise BoardError(400, 'Invalid page.')
    where = 'm.parent_id IS NULL' + (' AND m.category=?' if category else '')
    args = (category,) if category else ()
    with connect() as db:
        total = db.execute('SELECT count(*) FROM messages m WHERE '+where,args).fetchone()[0]
        rows = db.execute('''SELECT m.id,m.category,m.title,m.name,m.created_at,
          count(r.id) AS replies,coalesce(max(r.created_at),m.created_at) AS activity
          FROM messages m LEFT JOIN messages r ON r.parent_id=m.id WHERE '''+where+'''
          GROUP BY m.id ORDER BY activity DESC,m.id DESC LIMIT 50 OFFSET ?''',args+(offset,)).fetchall()
    return {'categories':config['categories'],'threads':[dict(row) for row in rows], 'total':total, 'offset':offset, 'page_size':50}

def thread(identifier):
    settings()
    with connect() as db:
        post = db.execute('SELECT * FROM messages WHERE id=? AND parent_id IS NULL',(identifier,)).fetchone()
        if not post:
            raise BoardError(404, 'This post is no longer available.')
        replies = db.execute('SELECT * FROM messages WHERE parent_id=? ORDER BY id',(identifier,)).fetchall()
        return {'post':public(post),'replies':[public(row) for row in replies]}

def create(payload, peer, parent=None):
    config = settings()
    expected = {'name','body'} if parent else {'name','body','title','category'}
    if set(payload) != expected:
        raise BoardError(400, 'Unexpected or missing message fields.')
    name = clean(payload['name'],'Display name',40,False) or 'Anonymous'
    body = clean(payload['body'],'Message',min(4000,config['body_characters']))
    category = payload.get('category','')
    title = clean(payload['title'],'Title',120) if not parent else ''
    if not parent and category not in config['categories']:
        raise BoardError(400, 'Choose a category.')
    code = secrets.token_urlsafe(18)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if parent:
            post = db.execute('SELECT category FROM messages WHERE id=? AND parent_id IS NULL',(parent,)).fetchone()
            if not post:raise BoardError(404, 'This post is no longer available.')
            category = post['category']
            if db.execute('SELECT count(*) FROM messages WHERE parent_id=?',(parent,)).fetchone()[0]>=min(200,config['max_replies']):
                raise BoardError(409, 'This conversation has reached its reply limit.')
        if db.execute('SELECT count(*) FROM messages').fetchone()[0]>=min(5000,config['max_messages']):
            raise BoardError(507, 'The board is full. Ask the caretaker to remove old conversations.')
        limit(db,peer,'posting',config['posts_per_minute_per_device'],config['posts_per_minute_total'])
        cursor = db.execute('INSERT INTO messages(parent_id,category,title,name,body,created_at,delete_hash) VALUES (?,?,?,?,?,?,?)',
           (parent,category,title,name,body,datetime.now(timezone.utc).isoformat(),hashlib.sha256(code.encode()).hexdigest()))
        identifier = cursor.lastrowid
    return {'id':identifier,'thread_id':parent or identifier,'deletion_code':code}

def remove(identifier, code=None, moderator=False, peer=''):
    settings()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT delete_hash,parent_id FROM messages WHERE id=?',(identifier,)).fetchone()
        if not row:raise BoardError(404, 'This message is no longer available.')
        if not moderator:
            limit(db,peer,'deletion',6)
            valid = isinstance(code,str) and code.isascii() and len(code)<=128 and hmac.compare_digest(row['delete_hash'],hashlib.sha256(code.encode()).hexdigest())
            if not valid:
                # Keep failed attempts even though the caller receives an error.
                db.commit()
                raise BoardError(403, 'Deletion code not accepted. Nothing was removed.')
        db.execute('DELETE FROM messages WHERE id=?',(identifier,))
    return {'removed':True,'thread_id':row['parent_id']}

def snapshot(destination):
    """SQLite online backup includes author-code hashes, never plaintext codes."""
    target = Path(destination)
    if target.is_symlink():raise ValueError('Refusing symlink backup destination.')
    temporary = target.with_suffix('.partial')
    if temporary.exists():temporary.unlink()
    fd = os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        with connect() as source:
            backup=sqlite3.connect(temporary)
            try:
                source.backup(backup)
                backup.execute('PRAGMA journal_mode=DELETE')
                if backup.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Board backup failed integrity check.')
            finally:
                backup.close()
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target

def notice_appearance(value, legacy=False):
    defaults={'color':'#fff0bd' if legacy else '#203e54','text_color':'auto' if legacy else '#d4af37','width':'full','margin':5,'margin_top':12,'margin_bottom':12,'font':'system','position':'top'}
    result={key:value.get(key,default) for key,default in defaults.items()}
    for key in ['color','text_color']:
        color=result[key]
        if key=='text_color' and color=='auto':continue
        if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise BoardError(400,'Choose six-digit background and text colors, or automatic text color.')
        result[key]=color.lower()
    if result['position'] not in ['top','below-header','bottom']:raise BoardError(400,'Choose top, below header, or fixed bottom.')
    if result['font'] not in ['system','old-english','serif','monospace']:raise BoardError(400,'Choose a supported banner font.')
    if result['width'] not in ['full','fit','margin']:raise BoardError(400,'Choose full width, fit text, or custom margins.')
    if type(result['margin']) not in [int,float] or not 0<=result['margin']<=40:raise BoardError(400,'Side margins must be between 0 and 40 percent.')
    for key in ['margin_top','margin_bottom']:
        if type(result[key]) not in [int,float] or not 0<=result[key]<=200:raise BoardError(400,'Top and bottom margins must be between 0 and 200 pixels.')
    return result

def notice():
    with connect() as db:
        row=db.execute('SELECT value FROM metadata WHERE key=?',('notice',)).fetchone()
    result=json.loads(row['value']) if row else {'text':'','updated_at':None}
    result.update(notice_appearance(result,legacy=bool(row)))
    return result

def set_notice(value,color=None,**appearance):
    text=clean(value,'Banner message',300,False)
    settings=notice()
    if color is not None:settings['color']=color
    settings.update(appearance)
    result={'text':text,**notice_appearance(settings),'updated_at':datetime.now(timezone.utc).isoformat()}
    with connect() as db:
        db.execute('INSERT INTO metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('notice',json.dumps(result)))
    return result
