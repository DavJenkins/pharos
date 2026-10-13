"""Bugout configuration, private state, readiness and idempotent requests."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
STATE = Path('/var/lib/dataark/bugout')
RUNTIME = Path('/run/dataark-bugout')
INTEGRATION = Path('/etc/dataark/bugout-ha.json')
KEYS = Path('/etc/dataark/bugout-keys')
ID = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
SMB = '/usr/bin/smbclient'
GPG = '/usr/bin/gpg'


def validate(config):
    if not isinstance(config, dict) or set(config) - {'tasks', 'reserve_gib', 'budget_seconds'}:
        raise ValueError('bugout accepts tasks and reserve_gib.')
    reserve = config.get('reserve_gib', 2)
    if type(reserve) is not int or not 1 <= reserve <= 1024:
        raise ValueError('bugout.reserve_gib must be an integer from 1 to 1024.')
    budget = config.get('budget_seconds', 300)
    if type(budget) is not int or not 10 <= budget <= 86400:
        raise ValueError('budget_seconds must be 10 to 86400.')
    tasks = config.get('tasks', [])
    if not isinstance(tasks, list) or len(tasks) > 16:
        raise ValueError('bugout.tasks must be a list of at most 16 tasks.')
    seen = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) - {'id','title','host','share','path','credential','priority','timeout_seconds','enabled','encryption','kind','mount','url','filename','prefetch','prefetch_interval','include_in_bugout','normal_sync','optional','estimated_seconds'}:
            raise ValueError('Unknown bugout task field.')
        key = task.get('id', '')
        if not isinstance(key, str) or not ID.fullmatch(key) or key in seen:
            raise ValueError('Bugout task IDs must be unique lowercase identifiers.')
        seen.add(key)
        if not isinstance(task.get('title'), str) or not task['title'].strip():
            raise ValueError('A bugout task needs a title.')
        kind = task.get('kind', 'smb')
        if kind not in ('smb','local','http'):
            raise ValueError('Bugout source kind must be smb, local or http.')
        if type(task.get('prefetch', False)) is not bool:
            raise ValueError('prefetch must be true or false.')
        for field in ('include_in_bugout','optional'):
            if type(task.get(field, field == 'include_in_bugout')) is not bool:
                raise ValueError(field + ' must be true or false.')
        if task.get('normal_sync','scheduled') not in ('manual','scheduled','when_available'):
            raise ValueError('normal_sync must be manual, scheduled or when_available.')
        if 'estimated_seconds' in task and (type(task['estimated_seconds']) is not int or task['estimated_seconds'] < 1):
            raise ValueError('estimated_seconds must be a positive integer.')
        interval = task.get('prefetch_interval', '1d')
        if not isinstance(interval,str) or not re.fullmatch(r'[1-9][0-9]*[mhdw]',interval):
            raise ValueError('prefetch_interval must be a duration such as 6h or 1d.')
        if kind == 'local':
            mount = task.get('mount','')
            if not isinstance(mount,str) or not re.fullmatch(r'/(?:mnt|media)/[A-Za-z0-9_./-]+',mount) or '..' in mount.split('/'):
                raise ValueError('Local sources require an explicit mount beneath /mnt or /media.')
        if kind == 'http':
            from urllib.parse import urlsplit
            target = task.get('url','')
            if not isinstance(target,str):
                raise ValueError('HTTP source requires a URL.')
            parsed = urlsplit(target)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or any(ord(c)<32 for c in target):
                raise ValueError('HTTP sources require an HTTP(S) URL without embedded credentials or fragments.')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', str(task.get('filename',''))):
                raise ValueError('HTTP sources require a safe filename.')
        if kind != 'smb' and task.get('credential'):
            raise ValueError('Named credentials currently apply to SMB sources only.')
        if kind == 'smb' and (not isinstance(task.get('host'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', task['host'])):
            raise ValueError('Use an SMB host name or IPv4 address without a port.')
        for field in ('share', 'path'):
            if kind != 'smb' and field == 'share':
                continue
            value = task.get(field, '' if field == 'path' else None)
            if not isinstance(value, str) or (field == 'share' and not value) or len(value) > 1024:
                raise ValueError('Invalid SMB share or path.')
            if any(ord(c) < 32 for c in value) or any(c in value for c in '\\;"*?') or value.startswith(('/', '-')):
                raise ValueError('SMB paths cannot contain control characters, wildcards or command delimiters.')
            if (field == 'share' and '/' in value) or any(p in ('.','..') for p in value.split('/')):
                raise ValueError('Use a share name and a relative directory path.')
        if task.get('credential') is not None and (not isinstance(task['credential'], str) or not ID.fullmatch(task['credential'])):
            raise ValueError('credential must be a named reference, not a password.')
        for field, default, low, high in (('priority',100,0,1000),('timeout_seconds',1800,10,86400)):
            value = task.get(field,default)
            if type(value) is not int or not low <= value <= high:
                raise ValueError('Invalid bugout ' + field)
        if type(task.get('enabled', True)) is not bool:
            raise ValueError('enabled must be true or false.')
        encryption = task.get('encryption', {})
        if not isinstance(encryption, dict) or set(encryption) - {'method','public_key'} or encryption.get('method','none') not in ('none','openpgp'):
            raise ValueError('Encryption supports none or openpgp.')
        if encryption.get('method') == 'openpgp' and not re.fullmatch(r'[A-Za-z0-9_-]+\.asc', str(encryption.get('public_key',''))):
            raise ValueError('OpenPGP requires a public_key filename ending in .asc.')
    return config


def configuration():
    from app.services.manifest import load_manifest
    manifest = load_manifest(ROOT / 'dataark.yaml')
    cfg = validate(manifest.get('bugout', {}))
    return cfg, Path(manifest['system']['base_mount'])


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextmanager
def database():
    if not STATE.is_dir():
        raise RuntimeError('Install the bugout worker on the Pi first.')
    db = sqlite3.connect(STATE / 'state.sqlite', timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, state TEXT, payload TEXT);'
                         'CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, operation TEXT);'
                         'CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT, next_try REAL DEFAULT 0, attempts INTEGER DEFAULT 0, sent INTEGER DEFAULT 0, error TEXT);')
        db.execute('CREATE TABLE IF NOT EXISTS prefetch (task_id TEXT PRIMARY KEY, signature TEXT, attempted REAL, payload TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS controls (operation_id TEXT PRIMARY KEY, continue_updates INTEGER NOT NULL)')
        yield db
    finally:
        db.close()


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode='w', encoding='utf-8') as stream:
        temp = Path(stream.name)
        os.chmod(temp, 0o600)
        json.dump(value, stream)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def healthy():
    try:
        return time.time() - (RUNTIME / 'heartbeat').stat().st_mtime < 45
    except OSError:
        return False


def heartbeat():
    (RUNTIME / 'heartbeat').touch(mode=0o600)


def read_credential(name, remembered_only=False):
    if not name:
        return None
    directories = (STATE / 'credentials',) if remembered_only else (RUNTIME, STATE / 'credentials')
    for directory in directories:
        path = directory / (name + '.json')
        try:
            value = json.loads(path.read_text())
            if value.get('expires', float('inf')) <= time.time():
                path.unlink(missing_ok=True)
                continue
            return value
        except FileNotFoundError:
            continue
    return None


def validate_credential(value):
    if not isinstance(value, dict) or set(value) != {'username','password','domain','remember'} or type(value['remember']) is not bool:
        raise ValueError('Supply username, password, domain and remember.')
    for key in ('username','password','domain'):
        if not isinstance(value[key], str) or len(value[key]) > 512 or any(ord(c) < 32 for c in value[key]):
            raise ValueError('Credentials must be single-line text of at most 512 characters.')
    if not value['username']:
        raise ValueError('Username is required.')
    return {key:value[key] for key in ('username','password','domain')}


def save_credential(task_id, value):
    cfg, _ = configuration()
    task = next((t for t in cfg.get('tasks', []) if t['id'] == task_id), None)
    if not task or not task.get('credential'):
        raise ValueError('Configure a named credential for this task first.')
    saved = validate_credential(value)
    with database() as db:
        if db.execute("SELECT 1 FROM operations WHERE state IN ('queued','running') LIMIT 1").fetchone():
            raise ValueError('Wait for the active backup before changing credentials.')
    name = task['credential']
    directory = STATE / 'credentials' if value['remember'] else RUNTIME
    if not value['remember']:
        saved['expires'] = time.time() + 3600
    atomic_json(directory / (name + '.json'), saved)
    if value['remember']:
        (RUNTIME / (name + '.json')).unlink(missing_ok=True)
        with database() as db:
            for source in cfg.get('tasks', []):
                if source.get('credential') == name:
                    db.execute('UPDATE prefetch SET attempted=0 WHERE task_id=?',(source['id'],))
            db.commit()


@contextmanager
def smb_command(task, remembered_only=False, credential=None):
    if credential is None:
        credential = read_credential(task.get('credential'), remembered_only)
    if task.get('credential') and credential is None:
        raise ValueError('Credentials required')
    args = [SMB, '//' + task['host'] + '/' + task['share'], '-d', '0', '-E', '-t', '10',
            '--option=client min protocol=SMB2']
    if task.get('path'):
        args += ['-D', task['path']]
    if credential:
        with tempfile.NamedTemporaryFile(dir=RUNTIME, mode='w', encoding='utf-8', delete=False) as stream:
            auth = Path(stream.name)
            os.chmod(auth, 0o600)
            stream.write(''.join(k + ' = ' + credential[k] + '\n' for k in ('username','password','domain')))
        try:
            yield args + ['-A', str(auth)]
        finally:
            auth.unlink(missing_ok=True)
    else:
        yield args + ['-N']


def prefetch_seconds(task):
    value = task.get('prefetch_interval', '1d')
    return int(value[:-1]) * {'m':60,'h':3600,'d':86400,'w':604800}[value[-1]]


def refresh_delay(task, cache):
    if cache.get('schedule_state',cache.get('state')) == 'completed':
        return prefetch_seconds(task)
    failures = cache.get('schedule_failure_count',cache.get('failure_count',1))
    return min(21600, 300 * 2 ** min(max(int(failures)-1,0),7))


def source_signature(task):
    return hashlib.sha256(json.dumps({k:v for k,v in task.items() if k not in ('priority','prefetch','prefetch_interval','normal_sync','include_in_bugout','optional','estimated_seconds','timeout_seconds','title','enabled')},sort_keys=True).encode()).hexdigest()


def local_source(task):
    mount = Path(task['mount'])
    if not mount.is_mount():
        raise ValueError('Source volume is not mounted')
    source = (mount / task.get('path','')).resolve()
    if not source.is_relative_to(mount.resolve()):
        raise ValueError('Source resolves outside its configured mount')
    _, root = configuration()
    for name in ('bugout-backups','.bugout-staging'):
        output = (root / name).resolve()
        if source == output or source.is_relative_to(output) or output.is_relative_to(source):
            raise ValueError('Source would include the backup destination')
    return source


def source_ready(task, remembered_only=False):
    kind = task.get('kind','smb')
    if remembered_only and task.get('credential') and read_credential(task['credential'], True) is None:
        return False, 'Remembered credentials required for prefetch'
    if kind == 'smb' and not Path(SMB).is_file():
        return False, 'SMB client is not installed'
    if task.get('encryption', {}).get('method') == 'openpgp':
        key = KEYS / task['encryption']['public_key']
        if not Path(GPG).is_file() or not key.is_file() or key.is_symlink():
            return False, 'Encryption public key or GPG is missing'
        try:
            checked = subprocess.run([GPG,'--homedir',str(STATE / 'gnupg'),'--batch','--with-colons',
                                      '--show-keys',str(key)],capture_output=True,timeout=3)
            if checked.returncode or b'pub:' not in checked.stdout or b'PRIVATE KEY' in key.read_bytes():
                return False, 'A valid public encryption key is required'
        except (OSError, subprocess.TimeoutExpired):
            return False, 'Cannot check encryption public key'
    if kind == 'local':
        try:
            source = local_source(task)
            if not (source.is_file() or source.is_dir()) or not os.access(source,os.R_OK):
                return False, 'Local source is missing or unreadable'
            if not Path('/usr/bin/tar').is_file():
                return False, 'tar is not installed'
            return True, 'Ready'
        except (OSError, ValueError) as error:
            return False, str(error) if type(error) is ValueError else 'Local source unavailable'
    if kind == 'http':
        if not Path('/usr/bin/curl').is_file():
            return False, 'curl is not installed'
        try:
            response = subprocess.run(['/usr/bin/curl','--head','--fail','--silent','--location',
                '--proto','=http,https','--proto-redir','=http,https','--max-time','5','--output',os.devnull,task['url']],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=6)
            return (True,'Ready') if response.returncode == 0 else (False,'HTTP source unavailable or does not support HEAD')
        except (OSError,subprocess.TimeoutExpired):
            return False, 'HTTP source unavailable or timed out'
    return probe_smb(task, remembered_only=remembered_only)


def probe_smb(task, remembered_only=False, credential=None):
    try:
        with smb_command(task, remembered_only=remembered_only, credential=credential) as args:
            result = subprocess.run(args + ['-c','ls'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=5)
        error = result.stderr.decode(errors='replace')
        if 'NT_STATUS_LOGON_FAILURE' in error or 'NT_STATUS_ACCESS_DENIED' in error:
            return False, 'Credentials rejected or access denied'
        if result.returncode or 'NT_STATUS_' in error:
            return False, 'Share or directory unavailable'
        return True, 'Ready'
    except ValueError as error:
        return False, str(error)
    except (OSError, subprocess.TimeoutExpired):
        return False, 'Share unavailable or timed out'


def test_credential(task_id, value):
    cfg, _ = configuration()
    task = next((t for t in cfg.get('tasks',[]) if t['id'] == task_id),None)
    if not task or task.get('kind','smb') != 'smb' or not task.get('credential'):
        raise ValueError('Configure an SMB source with a named credential first.')
    credential = validate_credential(value)
    if not Path(SMB).is_file():
        return {'ok':False,'message':'SMB client is not installed'}
    ok, reason = probe_smb(task, credential=credential)
    return {'ok':ok,'message':'Connection successful: share directory is readable. Credentials have not been saved.' if ok else reason}


def destination_ready(root, cfg):
    if not root.is_mount():
        return False, 'SSD is not mounted'
    try:
        if shutil.disk_usage(root).free < cfg.get('reserve_gib', 2) * 1024**3:
            return False, 'SSD space is below the reserve'
        folder = root / 'bugout-backups'
        if folder.is_symlink():
            return False, 'Unsafe backup directory'
        folder.mkdir(exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError:
        return False, 'Backup destination is not writable'
    return True, 'Ready'


def latest(db):
    for row in db.execute('SELECT payload FROM operations ORDER BY rowid DESC'):
        operation = json.loads(row[0])
        if operation.get('mode','bugout') == 'bugout':
            return operation
    return None


def fits_bugout(task, cfg):
    return task.get('include_in_bugout',True) and (not task.get('optional',False) or
        0 < task.get('estimated_seconds',0) <= cfg.get('budget_seconds',300))


def readiness():
    cfg, root = configuration()
    tasks = [t for t in cfg.get('tasks', []) if t.get('enabled', True)]
    if not tasks:
        return {'configured':False,'ready':False,'reason':'No bugout tasks configured','tasks':[], 'operation':None}
    if not healthy():
        common = 'Bugout worker unavailable'
    else:
        ok, reason = destination_ready(root, cfg)
        common = None if ok else reason
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        states = list(pool.map(lambda t: (False, common, None) if common else (*source_ready(t), now()), tasks))
    operation = None
    cached = {}
    prefetch_active = None
    ha = {'pending':0, 'error':None}
    if STATE.is_dir():
        with database() as db:
            operation = latest(db)
            for row in db.execute('SELECT * FROM prefetch'):
                task = next((t for t in tasks if t['id'] == row['task_id'] and source_signature(t) == row['signature']),None)
                if task:
                    cache = json.loads(row['payload'])
                    if task.get('prefetch',False) and task.get('normal_sync','scheduled') != 'manual':
                        due = row['attempted'] + refresh_delay(task,cache)
                        cache['next_attempt'] = datetime.fromtimestamp(due,timezone.utc).isoformat(timespec='seconds')
                    cached[task['id']] = cache
            for row in db.execute("SELECT payload FROM operations WHERE state IN ('queued','running')"):
                active = json.loads(row[0])
                if active.get('mode') == 'prefetch':
                    prefetch_active = active
            ha['pending'] = db.execute('SELECT count(*) FROM events WHERE sent=0').fetchone()[0]
            row = db.execute('SELECT error FROM events WHERE sent=0 AND error IS NOT NULL ORDER BY rowid DESC LIMIT 1').fetchone()
            ha['error'] = row[0] if row else None
    for task in tasks:
        cache = cached.get(task['id'])
        if cache and cache.get('file'):
            file = root / 'bugout-backups' / cache['file']
            if not file.is_file() or file.is_symlink():
                cache.pop('file',None)
                cache['message'] = 'Previously prefetched file is no longer available'
                cache['missing_file'] = True
    running = bool(operation and operation['state'] in ('queued','running'))
    entries = [{'id':t['id'],'title':t['title'],'credential_configured':bool(t.get('credential')),
                'credentials_saved':bool(read_credential(t.get('credential'))),
                'ready':ok,'reason':why,'checked':checked,'priority':t.get('priority',100),'prefetch':t.get('prefetch',False),
                'include_in_bugout':t.get('include_in_bugout',True),'bugout_ready':ok and fits_bugout(t,cfg),'normal_sync':t.get('normal_sync','scheduled'),
                'cache':cached.get(t['id'])} for t,(ok,why,checked) in zip(tasks,states)]
    ready = any(t['bugout_ready'] for t in entries) and not running
    return {'configured':True,'ready':ready,'bugout_configured':any(t['include_in_bugout'] for t in entries),
            'sync_ready':any(t['ready'] and t['prefetch'] for t in entries) and not running and not prefetch_active,'tasks':entries,'operation':operation,'prefetch_operation':prefetch_active,'home_assistant':ha,
            'reason':'Bugout already running' if running else 'Ready' if ready else common or 'No bugout source is ready within the configured time budget'}


def integration():
    try:
        return json.loads(INTEGRATION.read_text())
    except FileNotFoundError:
        return {}


def ha_authorized(header):
    try:
        saved = integration().get('inbound_token_sha256', '')
        if not header.startswith('Bearer ') or len(header) > 1024 or not saved:
            return False
        return hmac.compare_digest(hashlib.sha256(header[7:].encode()).hexdigest(), saved)
    except (OSError, ValueError, TypeError):
        return False


def event(db, operation, kind):
    # Credentials and source paths are never included in event payloads.
    if operation.get('mode') == 'prefetch':
        return
    cfg = integration()
    if cfg.get('url') and cfg.get('token'):
        payload = {'event_id':str(uuid.uuid4()),'kind':kind,'operation_id':operation['id'],
                   'origin':operation['origin'],'state':operation['state'], 'tasks':operation.get('results',[])}
        db.execute('INSERT INTO events(id,payload) VALUES (?,?)',(payload['event_id'],json.dumps(payload)))


def start(operation_id, origin, mode='bugout'):
    if not isinstance(operation_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{15,63}', operation_id):
        raise ValueError('operation_id must be a unique 16-64 character identifier (UUID or HA context ID).')
    with database() as db:
        existing = db.execute('SELECT o.payload FROM requests r JOIN operations o ON o.id=r.operation WHERE r.id=?',(operation_id,)).fetchone()
        if existing:
            return json.loads(existing[0])
    if mode not in ('bugout','prefetch'):
        raise ValueError('Invalid operation mode')
    available = readiness()  # Always probe again; never trust the browser's earlier readiness.
    cfg, root = configuration()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT o.payload FROM requests r JOIN operations o ON o.id=r.operation WHERE r.id=?',(operation_id,)).fetchone()
        if existing:
            db.rollback()
            return json.loads(existing[0])
        active = next((row for row in db.execute("SELECT id,payload FROM operations WHERE state IN ('queued','running')")
                       if json.loads(row['payload']).get('mode','bugout') == mode), None)
        if active:
            db.execute('INSERT INTO requests VALUES (?,?)',(operation_id,active['id']))
            db.commit()
            return json.loads(active['payload'])
        if not available.get('sync_ready' if mode == 'prefetch' else 'ready',False):
            db.rollback()
            raise ValueError(available['reason'])
        selected = {t['id'] for t in cfg.get('tasks',[]) if t.get('enabled',True) and (t.get('prefetch',False) if mode == 'prefetch' else t.get('include_in_bugout',True))}
        fitting = selected if mode == 'prefetch' else {t['id'] for t in cfg.get('tasks',[]) if fits_bugout(t,cfg)}
        ready_ids = {t['id'] for t in available['tasks'] if t['ready'] and t['id'] in selected and t['id'] in fitting}
        if not ready_ids:
            raise ValueError('No eligible sources are ready')
        payload = {'id':operation_id,'origin':origin,'mode':mode,'state':'queued','updated':now(),
                   'results':[{'id':t['id'],'title':t['title'],'state':'pending' if t['id'] in ready_ids else 'skipped',
                               'message':t['reason'] if t['id'] in fitting else 'Optional task does not fit the bugout time budget'} for t in available['tasks'] if t['id'] in selected]}
        # Snapshot job configuration separately from the public result.
        job = {'config':cfg,'root':str(root),'ready_ids':sorted(ready_ids)}
        atomic_json(STATE / (operation_id + '.job.json'), job)
        db.execute('INSERT INTO operations VALUES (?,?,?)',(operation_id,'queued',json.dumps(payload)))
        db.execute('INSERT INTO requests VALUES (?,?)',(operation_id,operation_id))
        event(db,payload,'trigger')
        db.commit()
        return payload


def update(operation, kind='status'):
    operation['updated'] = now()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE operations SET state=?,payload=? WHERE id=?',
                   (operation['state'],json.dumps(operation),operation['id']))
        if kind:
            event(db,operation,kind)
        db.commit()


def cancel(operation_id, continue_updates=False):
    if type(continue_updates) is not bool:
        raise ValueError('continue_updates must be true or false')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM operations WHERE id=?',(operation_id,)).fetchone()
        if not row:
            raise ValueError('Unknown operation')
        operation = json.loads(row[0])
        if operation.get('mode','bugout') != 'bugout':
            raise ValueError('This is not a bugout operation')
        if operation['state'] in ('queued','running'):
            # First cancellation wins, so retries cannot change its meaning.
            db.execute('INSERT OR IGNORE INTO controls VALUES (?,?)',(operation_id,int(continue_updates)))
            db.commit()
            return {'state':'cancelling','operation_id':operation_id}
        return operation


def cancellation(operation_id):
    with database() as db:
        row = db.execute('SELECT continue_updates FROM controls WHERE operation_id=?',(operation_id,)).fetchone()
        return None if row is None else bool(row[0])
