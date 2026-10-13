#!/usr/bin/env python3
"""Serial household snapshots and a retrying Home Assistant event outbox."""
from contextlib import contextmanager
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services import bugout as b


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def deliver_event():
    cfg = b.integration()
    if not cfg.get('url') or not cfg.get('token'):
        return
    target = cfg['url'].rstrip('/')
    parsed = urlsplit(target)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return
    with b.database() as db:
        row = db.execute('SELECT * FROM events WHERE sent=0 ORDER BY rowid LIMIT 1').fetchone()
        if row is None or row['next_try'] > time.time():
            return
        try:
            request = Request(target + '/api/events/dataark_bugout', data=row['payload'].encode(),
                              headers={'Authorization':'Bearer ' + cfg['token'],'Content-Type':'application/json'}, method='POST')
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=4) as response:
                if response.status != 200:
                    raise ValueError('Unexpected response')
            db.execute('UPDATE events SET sent=1,error=NULL WHERE id=?',(row['id'],))
        except Exception:
            delay = min(300, 5 * 2 ** min(row['attempts'],6))
            db.execute('UPDATE events SET attempts=attempts+1,next_try=?,error=? WHERE id=?',
                       (time.time()+delay,'Home Assistant delivery failed; retrying',row['id']))
        db.commit()


def terminate(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class BugoutCancelled(RuntimeError):
    pass


class BudgetExpired(RuntimeError):
    pass


def check_control(operation):
    if operation.get('mode','bugout') == 'bugout':
        if b.cancellation(operation['id']) is not None:
            raise BugoutCancelled('Bugout cancelled')
        if operation.get('deadline') and time.time() >= operation['deadline']:
            raise BudgetExpired('Bugout time budget reached')
    elif bugout_pending():
        raise PrefetchYield('Background refresh yielded to bugout')


class PrefetchYield(RuntimeError):
    pass


def bugout_pending():
    with b.database() as db:
        return any(json.loads(row[0]).get('mode','bugout') == 'bugout'
                   for row in db.execute("SELECT payload FROM operations WHERE state='queued'"))


@contextmanager
def producer_command(task, prefetch=False):
    kind = task.get('kind','smb')
    if kind == 'smb':
        with b.smb_command(task, remembered_only=prefetch) as args:
            yield args + ['-Tc','-']
    elif kind == 'local':
        source = b.local_source(task)
        # Never follow source symlinks into another mount or private system directories.
        yield ['/usr/bin/tar','--one-file-system','-cf','-','-C',str(source.parent),'--',source.name]
    else:
        yield ['/usr/bin/curl','--fail','--silent','--show-error','--location',
               '--proto','=http,https','--proto-redir','=http,https','--connect-timeout','10',
               '--max-time',str(task.get('timeout_seconds',1800)),'--output','-',task['url']]


def copy_task(task, root, cfg, operation, result):
    check_control(operation)
    ok, message = b.destination_ready(root, cfg)
    if not ok:
        raise RuntimeError(message)
    prefetch = operation.get('mode') == 'prefetch'
    remembered_only = prefetch and operation.get('origin') == 'scheduler'
    ok, message = b.source_ready(task, remembered_only=remembered_only)
    if not ok:
        raise RuntimeError(message)
    stage = root / '.bugout-staging'
    if stage.is_symlink():
        raise RuntimeError('Unsafe staging directory')
    stage.mkdir(exist_ok=True)
    encrypted = task.get('encryption',{}).get('method') == 'openpgp'
    suffix = ('-' + task['filename']) if task.get('kind') == 'http' else '.tar'
    if encrypted:
        suffix += '.gpg'
    prefix = ('prefetch-' + b.source_signature(task)[:16]) if prefetch else operation['id']
    filename = task['id'] + '-' + prefix + suffix
    final = root / 'bugout-backups' / filename
    partial = stage / (task['id'] + '-' + operation['id'] + suffix + '.part')
    if (final.exists() and not prefetch) or final.is_symlink() or partial.exists() or partial.is_symlink():
        raise RuntimeError('Snapshot filename already exists; refusing to overwrite')
    producer = consumer = None
    started = time.monotonic()
    completed = False
    try:
        with producer_command(task, remembered_only) as command, partial.open('xb') as output, tempfile.TemporaryFile(dir=b.RUNTIME) as errors:
            # Credentials are in a private short-lived auth file, never command arguments.
            check_control(operation)
            producer = subprocess.Popen(command, stdout=subprocess.PIPE if encrypted else output,
                                        stderr=errors, stdin=subprocess.DEVNULL)
            if encrypted:
                key = b.KEYS / task['encryption']['public_key']
                consumer = subprocess.Popen([b.GPG,'--homedir',str(b.STATE / 'gnupg'),'--batch','--yes',
                    '--recipient-file',str(key),'--trust-model','always','--encrypt','--output','-'],
                    stdin=producer.stdout, stdout=output, stderr=errors)
                producer.stdout.close()
            while producer.poll() is None or (consumer and consumer.poll() is None):
                b.heartbeat()
                check_control(operation)
                if time.monotonic() - started > task.get('timeout_seconds',1800):
                    raise RuntimeError('Task timed out')
                if not root.is_mount() or shutil.disk_usage(root).free < cfg.get('reserve_gib',2) * 1024**3:
                    raise RuntimeError('SSD unavailable or free-space reserve reached')
                if os.fstat(errors.fileno()).st_size > 1024**2:
                    raise RuntimeError('Backup produced excessive errors')
                result['bytes_written'] = partial.stat().st_size
                b.update(operation, kind=None)
                time.sleep(2)
            output.flush()
            os.fsync(output.fileno())
            errors.seek(0)
            error = errors.read(1024**2).decode(errors='replace')
            if consumer and consumer.returncode:
                raise RuntimeError('Encryption failed (GPG exit ' + str(consumer.returncode) + '); check the recipient public key')
            if producer.returncode or 'NT_STATUS_' in error:
                # Report only status codes, never raw stderr, filenames, or credentials.
                statuses = sorted(set(re.findall(r'\bNT_STATUS_[A-Z0-9_]+\b',error)))[:4]
                detail = '; ' + ', '.join(statuses) if statuses else ''
                raise RuntimeError('Source copy failed (exit ' + str(producer.returncode) + ')' + detail)
        if not partial.stat().st_size:
            raise RuntimeError('Empty snapshot output')
        if not encrypted and task.get('kind','smb') != 'http':
            # Check structure without extracting or executing household files.
            with tarfile.open(partial, 'r:') as archive:
                for member in archive:
                    b.heartbeat()
                    check_control(operation)
                    if time.monotonic() - started > task.get('timeout_seconds',1800):
                        raise RuntimeError('Snapshot structure check timed out')
        check_control(operation)
        result['bytes_written'] = partial.stat().st_size
        os.replace(partial, final)
        completed = True
        result['file'] = filename
    finally:
        terminate(producer)
        terminate(consumer)
        if not completed:
            partial.unlink(missing_ok=True)


def run_operation(operation):
    operation['state'] = 'running'
    b.update(operation)
    try:
        job = json.loads((b.STATE / (operation['id'] + '.job.json')).read_text())
        cfg, root = b.validate(job['config']), Path(job['root'])
        if operation.get('mode','bugout') == 'bugout':
            operation['deadline'] = time.time() + cfg.get('budget_seconds',300)
        results = {entry['id']:entry for entry in operation['results']}
        for task in sorted(cfg['tasks'], key=lambda t:t.get('priority',100)):
            if task['id'] not in job['ready_ids']:
                continue
            result = results[task['id']]
            if result['state'] == 'completed':
                continue
            check_control(operation)
            if operation.get('mode','bugout') == 'bugout' and task.get('optional',False):
                remaining = operation['deadline'] - time.time()
                estimate = task.get('estimated_seconds')
                if estimate is None or estimate > remaining:
                    result.update(state='skipped',message='Optional task has no fitting time estimate')
                    continue
            result.update(state='copying', message='Creating snapshot', bytes_written=0)
            b.update(operation)
            deliver_event()
            try:
                copy_task(task, root, cfg, operation, result)
                result.update(state='completed', message='Snapshot saved')
            except (PrefetchYield,BugoutCancelled,BudgetExpired):
                raise
            except Exception as error:
                # Only our controlled messages go to the public API; never SMB output.
                result.update(state='failed', message=str(error) if type(error) is RuntimeError else 'Snapshot failed')
            if operation.get('mode') == 'prefetch':
                record_prefetch(task, result, preserve_schedule=operation.get('origin') == 'cancel_handoff')
            b.update(operation)
            b.heartbeat()
        states = [entry['state'] for entry in operation['results']]
        operation['state'] = 'completed' if all(s == 'completed' for s in states) else 'partial' if 'completed' in states else 'failed'
    except (PrefetchYield,BugoutCancelled,BudgetExpired) as error:
        operation['state'] = 'cancelled' if isinstance(error,BugoutCancelled) else 'queued' if isinstance(error,PrefetchYield) else 'interrupted'
        for result in operation['results']:
            if result['state'] in ('pending','copying'):
                result.update(state='pending' if isinstance(error,PrefetchYield) else 'interrupted',message=str(error))
        if operation.get('mode') == 'prefetch' and operation['state'] != 'queued':
            for task in cfg['tasks']:
                if task['id'] in results:
                    record_prefetch(task,results[task['id']],preserve_schedule=operation.get('origin') == 'cancel_handoff')
    except Exception:
        operation['state'] = 'failed'
        operation['error'] = 'Unable to process the configured job'
    finally:
        # Use-once credentials are never retained beyond this operation.
        try:
            for task in job['config']['tasks']:
                if operation['state'] != 'queued' and operation.get('origin') != 'scheduler' and b.cancellation(operation['id']) is not True and task.get('credential'):
                    (b.RUNTIME / (task['credential'] + '.json')).unlink(missing_ok=True)
        except (NameError, KeyError):
            pass
        finish_operation(operation, locals().get('job'))
        if operation['state'] != 'queued':
            (b.STATE / (operation['id'] + '.job.json')).unlink(missing_ok=True)



def finish_operation(operation, job):
    # Final state, cancellation notification, and handoff are committed together.
    with b.database() as db:
        db.execute('BEGIN IMMEDIATE')
        control = db.execute('SELECT continue_updates FROM controls WHERE operation_id=?',(operation['id'],)).fetchone()
        if control and operation.get('mode','bugout') == 'bugout':
            operation['state'] = 'cancelled'
            if control[0] and job:
                unfinished = {v['id'] for v in operation['results'] if v['state'] != 'completed'}
                tasks = [t for t in job['config']['tasks'] if t['id'] in unfinished]
                if tasks:
                    key = operation['id'] + '-background'
                    continuation = {'id':key,'mode':'prefetch','origin':'cancel_handoff','state':'queued','updated':b.now(),
                        'results':[{'id':t['id'],'title':t['title'],'state':'pending','message':'Continuing as normal maintenance'} for t in tasks]}
                    b.atomic_json(b.STATE / (key + '.job.json'),{'root':job['root'],
                        'config':{'tasks':tasks,'reserve_gib':job['config'].get('reserve_gib',2)},'ready_ids':[t['id'] for t in tasks]})
                    db.execute('INSERT OR IGNORE INTO operations VALUES (?,?,?)',(key,'queued',json.dumps(continuation)))
                    operation['background_operation_id'] = key
        operation['updated'] = b.now()
        db.execute('UPDATE operations SET state=?,payload=? WHERE id=?',(operation['state'],json.dumps(operation),operation['id']))
        b.event(db,operation,'cancelled' if operation['state'] == 'cancelled' else 'completed')
        db.commit()


def record_prefetch(task, result, preserve_schedule=False):
    signature = b.source_signature(task)
    with b.database() as db:
        row = db.execute('SELECT * FROM prefetch WHERE task_id=?',(task['id'],)).fetchone()
        cache = json.loads(row['payload']) if row and row['signature'] == signature else {}
        schedule_state = cache.get('schedule_state',cache.get('state','unavailable'))
        if preserve_schedule:
            cache.setdefault('schedule_failure_count',cache.get('failure_count',1))
            cache['schedule_state'] = schedule_state
        else:
            cache.pop('schedule_state',None)
            cache.pop('schedule_failure_count',None)
        cache['failure_count'] = 0 if result['state'] == 'completed' else cache.get('failure_count',0) + 1
        cache.update(state=result['state'], message=result['message'], checked=b.now())
        if result['state'] == 'completed':
            cache.update(file=result['file'],last_success=b.now(),bytes_written=result.get('bytes_written',0))
        db.execute('INSERT OR REPLACE INTO prefetch VALUES (?,?,?,?)',
                   (task['id'],signature,(row['attempted'] if row and row['signature'] == signature else 0) if preserve_schedule else time.time(),json.dumps(cache)))
        db.commit()


def queue_prefetch():
    cfg, root = b.configuration()
    tasks = [t for t in cfg.get('tasks',[]) if t.get('enabled',True) and t.get('prefetch',False) and t.get('normal_sync','scheduled') != 'manual']
    if not tasks:
        return
    with b.database() as db:
        if db.execute("SELECT 1 FROM operations WHERE state IN ('queued','running') LIMIT 1").fetchone():
            return
    ok, _ = b.destination_ready(root,cfg)
    if not ok:
        return
    for task in sorted(tasks,key=lambda t:t.get('priority',100)):
        b.heartbeat()
        signature = b.source_signature(task)
        with b.database() as db:
            row = db.execute('SELECT * FROM prefetch WHERE task_id=?',(task['id'],)).fetchone()
        reconnected = False
        if task.get('normal_sync') == 'when_available':
            with b.database() as db:
                db.execute('CREATE TABLE IF NOT EXISTS availability (id TEXT PRIMARY KEY, checked REAL, online INTEGER)')
                previous = db.execute('SELECT * FROM availability WHERE id=?',(task['id'],)).fetchone()
                if previous and time.time() - previous['checked'] < 300:
                    continue
                online, reason = b.source_ready(task,remembered_only=True)
                reconnected = online and (not previous or not previous['online'])
                db.execute('INSERT OR REPLACE INTO availability VALUES (?,?,?)',(task['id'],time.time(),int(online)))
                db.commit()
            if not online:
                continue
        if row and row['signature'] == signature and not reconnected:
            old = json.loads(row['payload'])
            delay = b.refresh_delay(task,old)
            if time.time() - row['attempted'] < delay:
                continue
        ok, reason = b.source_ready(task, remembered_only=True)
        if not ok:
            record_prefetch(task,{'state':'unavailable','message':reason})
            continue
        operation_id = str(__import__('uuid').uuid4())
        operation = {'id':operation_id,'origin':'scheduler','mode':'prefetch','state':'queued','updated':b.now(),
                     'results':[{'id':task['id'],'title':task['title'],'state':'pending','message':'Scheduled prefetch'}]}
        with b.database() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM operations WHERE state IN ('queued','running') LIMIT 1").fetchone():
                db.rollback();return
            b.atomic_json(b.STATE / (operation_id + '.job.json'),
                          {'config':{'tasks':[task],'reserve_gib':cfg.get('reserve_gib',2)},'root':str(root),'ready_ids':[task['id']]})
            db.execute('INSERT INTO operations VALUES (?,?,?)',(operation_id,'queued',json.dumps(operation)))
            db.commit()
        return


def main():
    import fcntl
    os.umask(0o077)
    with (b.RUNTIME / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # A stopped job is never silently reported as successful or automatically recopied.
        with b.database() as db:
            interrupted = [json.loads(row[0]) for row in db.execute("SELECT payload FROM operations WHERE state='running'")]
        for op in interrupted:
            op.update(state='interrupted',error='Worker restarted; inspect partial files before retrying')
            for result in op.get('results', []):
                if result['state'] in ('copying','pending'):
                    result.update(state='interrupted',message='Worker restarted')
            b.update(op,'completed')
        while True:
            b.heartbeat()
            deliver_event()
            try:
                queue_prefetch()
            except (OSError, ValueError, RuntimeError):
                pass  # Invalid configuration/readiness is reported by the API; keep the worker alive.
            with b.database() as db:
                pending = [json.loads(row[0]) for row in db.execute("SELECT payload FROM operations WHERE state='queued' ORDER BY rowid")]
            if pending:
                pending.sort(key=lambda op:op.get('mode') == 'prefetch')
                run_operation(pending[0])
            time.sleep(2)


if __name__ == '__main__':
    main()
