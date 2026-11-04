#!/usr/bin/env python3
"""Prepare, compare and explicitly accept configured publisher candidates.

Only registered source URLs are used. Nothing downloaded is executed. Each
decision is bound to a prepared job and the source revision it reviewed.
"""
from contextlib import contextmanager
import copy
import difflib
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services import reference_checks as checks
from app.services.manifest import load_manifest, inside, atomic_write
from app.services.publisher_review import revision

STATE = Path('/var/lib/dataark/publisher-review')
UPDATES_LOCK = Path('/var/lib/dataark/updates/worker.lock')


def digest(path, progress=None):
    h = hashlib.sha256()
    amount=0;total=path.stat().st_size
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024**2), b''):
            h.update(chunk);amount+=len(chunk)
            if progress:progress(amount,total)
    return h.hexdigest()


def install_phase(value, phase, done=0, total=0):
    value['install_telemetry']={'phase':phase,'bytes_processed':done,'total_bytes':total}
    if total:value['install_telemetry']['percent']=min(100,done*100/total)
    save(value['asset_id'],value)


def installed_digest(path,value,phase):
    last=[0]
    def report(done,total):
        now=time.monotonic()
        if now-last[0]>=3 or done==total:
            install_phase(value,phase,done,total);last[0]=now
    install_phase(value,phase,0,path.stat().st_size)
    return digest(path,report)


def file_version(path):
    stat = path.stat()
    # exFAT inode numbers can change after cache eviction without any file edit.
    # This cheap gate is followed by a full SHA-256 check before applying a decision.
    return [stat.st_size, stat.st_mtime_ns]


def save(asset_id, value):
    import pwd
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o750)
    os.chown(STATE, 0, pwd.getpwnam('admin').pw_gid)
    path = STATE / (asset_id + '.json')
    value['updated_at'] = time.time()
    atomic_write(path, (json.dumps(value, indent=2) + '\n').encode())
    path.chmod(0o640)
    os.chown(path, 0, pwd.getpwnam('admin').pw_gid)


@contextmanager
def locked(blocking=False):
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'worker.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError: raise ValueError('Another publisher review is running. Wait for it to finish.') from None
        yield


def asset_record(asset_id):
    manifest = load_manifest(ROOT / 'dataark.yaml')
    asset = next((a for a in manifest['assets'] if a['id'] == asset_id and not a.get('removed')), None)
    if not asset: raise ValueError('Registered collection not found')
    mount = Path(manifest['system']['base_mount'])
    if not mount.is_mount(): raise ValueError('Library storage is not mounted')
    path = inside(mount, asset['relative_path'])
    if not path.is_file() or path.is_symlink(): raise ValueError('Installed reference is not a regular file')
    source = checks.source(asset)
    record = checks.read(checks.STATE, {'sources': {}})['sources'].get(source, {})
    if not source: raise ValueError('No publisher source configured')
    return manifest, asset, mount, path, source, record


def notify(value):
    from app.services.collection_changes import safe_record
    kind = {'queued': 'queued', 'preparing': 'downloading', 'ready': 'verifying',
            'installing': 'activating', 'installed': 'installed', 'kept': 'configuration_published', 'failed': 'failed'}[value['state']]
    safe_record(kind, collection_id=value['asset_id'], title=value['title'],
                operation_id=value['job'], action='publisher_review', activity_key='publisher_review')


def submit(payload):
    if not isinstance(payload, dict) or set(payload) != {'action', 'asset_id', 'decision', 'job'}:
        raise ValueError('Invalid publisher review request')
    asset_id = payload['asset_id']
    if not isinstance(asset_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,160}', asset_id): raise ValueError('Invalid collection')
    if payload['decision'] not in ('prepare', 'install', 'keep'): raise ValueError('Invalid review decision')
    from app.services.publisher_review import status
    with locked():
        old = status(asset_id)
        if old.get('state') in ('interrupted', 'failed') and old.get('transaction'):
            recover(old)
        if old.get('state') in ('queued', 'preparing', 'installing'):
            # A dead worker must not leave a permanent spinner.
            unit = 'dataark-publisher-review-' + old['job']
            active = subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0
            if active: raise ValueError('This review is already running')
            old.update(state='failed', message='Review was interrupted. Prepare it again.'); save(asset_id, old)
        manifest, asset, mount, path, source, record = asset_record(asset_id)
        if payload['decision'] == 'prepare':
            job = uuid.uuid4().hex
            value = {'state': 'queued', 'job': job, 'asset_id': asset_id, 'title': asset['title'],
                     'revision': revision(record), 'installed_version': file_version(path),
                     'started_at': time.time(), 'operation_started_at': time.time(),
                     'message': 'Queued: preparing a verified comparison. Installed copy remains available.'}
            if old.get('installed_version') == value['installed_version'] and re.fullmatch(r'[a-f0-9]{64}',old.get('installed_hash','')):
                value['installed_hash']=old['installed_hash']
            if asset_id == 'osm-massachusetts':
                filesystem=subprocess.check_output(['findmnt','-n','-o','FSTYPE','--target',str(mount)],text=True,timeout=10).strip()
                if filesystem == 'exfat':
                    if shutil.disk_usage(STATE).free < path.stat().st_size+4*1024**3:
                        raise ValueError('This exFAT library needs sufficient Linux-system-drive scratch space to build the map safely')
                    value['system_staging']=True
            value['candidate_edition'] = (record.get('edition_discovery') or {}).get('candidate',{}).get('edition') if (record.get('edition_discovery') or {}).get('candidate') else None
        else:
            if old.get('state') != 'ready' or payload['job'] != old.get('job'): raise ValueError('Prepare and review this candidate first')
            if revision(record) != old['revision'] or file_version(path) != old['installed_version']:
                raise ValueError('Source or installed file changed. Prepare a fresh comparison.')
            value = dict(old, state='installing', decision=payload['decision'], operation_started_at=time.time(), message='Applying your review decision; existing files are retained.')
            job = value['job']
        save(asset_id, value)
        try:
            subprocess.run(['systemd-run', '--quiet', '--collect', '--unit=dataark-publisher-review-' + job,
                '--property=MemoryMax=900M', '--property=CPUQuota=150%',
                '--property=OOMScoreAdjust=500', '--property=OOMPolicy=stop',
                '--setenv=GOMEMLIMIT=550MiB', '--setenv=GOGC=50', '--setenv=GOMAXPROCS=2',
                '--property=RuntimeMaxSec=6h',
                str(ROOT / 'venv/bin/python'), str(ROOT / 'tools/publisher_review.py'), asset_id, job], check=True, capture_output=True)
        except Exception:
            value.update(state='failed', message='Unable to start the review worker. Nothing installed.'); save(asset_id, value); raise
        notify(value)
        return value


def plain(path):
    from tools.check_reference_sources import Text
    if path.suffix.lower() == '.pdf':
        return subprocess.check_output(['pdftotext', '-layout', str(path), '-'], text=True, timeout=60)[:2_000_000]
    raw = path.read_text(errors='replace')
    boundary = re.search(r'(?:Original publisher page \(internet\)|Publisher source)</a></(?:div|p)>', raw)
    if boundary: raw = raw[boundary.end():]
    p = Text(); p.feed(raw)
    text = '\n'.join(' '.join(part.split()) for part in p.parts if part.strip())[:2_000_000]
    # The Virginia publisher prints today's date in the document banner.
    # Do not present that banner clock as an amendment to the constitution.
    text = re.sub(r'(Constitution of Virginia)\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}/\d{1,2}/\d{4}', r'\1', text)
    return text


def comparison(old, new):
    before, after = plain(old).splitlines(), plain(new).splitlines()
    diff = list(difflib.unified_diff(before, after, fromfile='Installed', tofile='Publisher candidate', n=2))
    return {'identical': before == after, 'diff': '\n'.join(diff[:1200]), 'diff_truncated': len(diff) > 1200}


def command(value, args):
    """Expose the builder's bounded status line, never its unbounded log."""
    log = Path(args[3]).parent/'builder.log' if len(args)>3 and args[1]=='extract' else STATE/(value['job']+'.log')
    with log.open('ab') as output, subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT) as process:
        while process.poll() is None:
            if shutil.disk_usage(log.parent).free < 2*1024**3:
                process.terminate()
                raise ValueError('Map staging stopped to preserve free system space; installed map retained')
            telemetry={'elapsed_seconds':round(time.time()-value.get('started_at',time.time()))}
            try:
                proc=Path('/proc')/str(process.pid)
                io=dict(line.split(': ',1) for line in (proc/'io').read_text().splitlines())
                telemetry['bytes_processed']=int(io.get('rchar',0))
                if value.get('cache_directory'):
                    cache=Path(value['cache_directory'])
                    telemetry['bytes_downloaded']=sum(p.stat().st_size for p in cache.glob('*') if p.suffix in ('.bin','.part'))
                process_status=(proc/'status').read_text()
                for field,key in [('VmRSS','memory_bytes'),('VmSwap','swap_bytes')]:
                    match=re.search(r'^'+field+r':\s+(\d+) kB',process_status,re.M)
                    if match:telemetry[key]=int(match[1])*1024
                with log.open('rb') as stream:
                    stream.seek(0,2);end=stream.tell();stream.seek(max(0,end-4096));tail=stream.read().decode(errors='replace')
                percentages=re.findall(r'fetching chunks\s+(\d+)%',tail)
                if percentages and int(percentages[-1])>0:telemetry['percent']=int(percentages[-1])
                telemetry['phase']='Downloading map tiles' if percentages else 'Planning regional extraction' if args[1]=='extract' else 'Verifying map archive'
                value.update(message=telemetry['phase']+'. The installed map remains available.',telemetry=telemetry)
                save(value['asset_id'],value)
            except OSError:pass
            time.sleep(3)
        if process.wait():
            with log.open('rb') as stream:
                stream.seek(0,2);end=stream.tell();stream.seek(max(0,end-1000));error=stream.read().decode(errors='replace')
            raise ValueError('Candidate builder failed: '+error[-500:])


def prepare(value, asset, mount, installed, source, record, stage):
    from tools.check_reference_sources import check
    candidate = (record.get('edition_discovery') or {}).get('candidate')
    result = check(source, [asset], {}, checks.settings(), mount)
    # Keep the exact review baseline even when a date-family candidate is present.
    value['checked'] = result
    value['files'] = []
    def add(path, relative):
        value['files'].append({'file': path.name, 'relative_path': relative, 'sha256': digest(path), 'bytes': path.stat().st_size})
    if candidate and candidate.get('kind') == 'map_extraction':
        config = checks.read(ROOT / 'deploy/reference/osm-usa.json', {})
        if asset['id'] != 'osm-massachusetts' or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',candidate.get('edition','')) or candidate['archive_url']!='https://build.protomaps.com/'+candidate['edition'].replace('-','')+'.pmtiles':
            raise ValueError('Unsupported map build')
        if shutil.disk_usage(mount).free < config['reserve_gib'] * 1024**3: raise ValueError('Insufficient map staging space')
        if shutil.disk_usage(mount).free < installed.stat().st_size*3+1024**3: raise ValueError('Insufficient space for resumable source ranges, the candidate, and a retained previous map')
        target = stage / 'usa.pmtiles'
        # Use the tested HTTP/1.1 retry/cache adapter instead of letting a single
        # long upstream range request strand the Go extractor. It is loopback only.
        from tools import map_range_source as ranges
        from http.server import ThreadingHTTPServer
        import threading
        ranges.SOURCE=candidate['archive_url']
        ranges.CACHE=mount/'.publisher-review-cache'/candidate['edition']
        ranges.META=None
        value['cache_directory']=str(ranges.CACHE)
        server=ThreadingHTTPServer(('127.0.0.1',0),ranges.Handler)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            command(value, ['/usr/local/bin/pmtiles', 'extract', 'http://127.0.0.1:'+str(server.server_port)+'/source.pmtiles', str(target),
                '--region=' + str(inside(ROOT, config['region'])), '--maxzoom=' + str(config['maxzoom']), '--download-threads=2'])
        finally:server.shutdown();server.server_close()
        value['message'] = 'Verifying the regional map archive…'; save(asset['id'], value)
        command(value, ['/usr/local/bin/pmtiles', 'verify', str(target)])
        header = json.loads(subprocess.check_output(['/usr/local/bin/pmtiles', 'show', str(target), '--header-json'], text=True))
        if header.get('maxzoom') != config['maxzoom']: raise ValueError('Map zoom verification failed')
        value['edition'] = candidate; value['kind'] = 'map'; add(target, asset['relative_path'])
        metadata = dict(config,source=candidate['archive_url'],sha256=value['files'][0]['sha256'],bytes=value['files'][0]['bytes'])
        meta = stage / 'source.json'; meta.write_text(json.dumps(metadata,indent=2))
        add(meta,str(Path(asset['relative_path']).parent/'source.json'))
        value['summary'] = 'Verified regional extraction of ' + candidate['edition'] + '. Same configured coverage; the previous map is retained.'
    elif asset['id'] in ('callbook-callsigns-sqlite', 'callbook-fcc-amateur-source-zip'):
        from tools import install_callsigns as callbook
        callbook.ROOT = stage
        callbook.acquire(stage / 'fcc-amateur-source.zip', callbook.FCC, 400 * 1024**2, True)
        shutil.copyfile(mount / 'civic-reference/zcta-2025.zip', stage / 'zcta-2025.zip')
        callbook.build()
        for name in ('fcc-amateur-source.zip', 'callsigns.sqlite', 'callsigns-source.json'): add(stage / name, 'civic-reference/' + name)
        value['kind'] = 'callbook'
        meta = json.loads((stage / 'callsigns-source.json').read_text())
        value['summary'] = 'Verified FCC database: ' + str(meta['license_count']) + ' licenses; ' + str(meta['zip_matched_count']) + ' with approximate ZIP locations. Updates the database and its source ZIP together.'
    else:
        value['kind'] = 'document'
        target = stage / ('candidate' + installed.suffix)
        if candidate:
            from tools.edition_discovery import fetch, validate, pdf_edition, period_date, PublisherRedirect
            from urllib.request import build_opener
            rules = checks.read(ROOT / 'deploy/reference/edition-discovery.json', {})['rules']
            rule = rules[asset['id']]; hosts = validate(rule)
            raw = fetch(candidate['url'], hosts, rule.get('max_bytes', 16 * 1024**2), build_opener(PublisherRedirect(hosts)).open)
            sha = pdf_edition(raw, rule, period_date(candidate['edition'], rule.get('period', 'year')))
            if sha != candidate['sha256']: raise ValueError('Publisher edition changed. Check sources and prepare again.')
            target.write_bytes(raw); value['edition'] = candidate
        elif installed.suffix == '.html':
            from tools import install_resilience as resilience
            chapter = re.search(r'/Chapter([0-9A-Za-z]+)/?$', source)
            if __import__('urllib.parse', fromlist=['urlsplit']).urlsplit(source).hostname == 'malegislature.gov' and chapter:
                resilience.MOUNT = stage
                row = resilience.chapter(source, chapter[1], asset['title'])
                if row.get('status') != 'installed' or row.get('missing_sections'): raise ValueError('Chapter sections were not all retrieved; installed chapter retained')
                shutil.copyfile(stage / 'civic-reference' / row['filename'], target)
            else:
                from tools.install_jurisdictions import fetch
                raw, resolved = fetch(source)
                body, _ = resilience.body_copy(raw, source)
                target.write_bytes(resilience.document(asset['title'], body, resolved, 'Publisher snapshot at review'))
        elif installed.suffix == '.pdf':
            from tools.install_jurisdictions import fetch
            raw, _ = fetch(source)
            if not raw.startswith(b'%PDF-'): raise ValueError('Publisher did not return a PDF')
            target.write_bytes(raw)
            subprocess.run(['pdfinfo', str(target)], check=True, stdout=subprocess.DEVNULL)
            rules=checks.read(ROOT/'deploy/reference/edition-discovery.json',{}).get('rules',{})
            if asset['id'] in rules:
                from tools.edition_discovery import pdf_edition,period_date
                rule=rules[asset['id']]
                pdf_edition(raw,rule,period_date(rule['current_edition'],rule.get('period','year')))
            else:
                from tools.import_browser_reference import IDENTITY,validate_pdf
                identifier=next((i for i in IDENTITY if asset['id']==i or asset['id'].endswith('-'+i)),None)
                if identifier:validate_pdf(raw,identifier)
        else: raise ValueError('No verified acquisition adapter for this reference; installed copy retained')
        value.update(comparison(installed, target))
        add(target, asset['relative_path'])
        value['summary'] = ('A separate ' + candidate['edition'] + ' edition will be added; the existing edition keeps its own link.' if candidate else 'Review the text comparison below. The previous file is retained when replaced.')
    # Avoid acknowledging metadata for a newer rolling ZIP/map than the one prepared.
    if value['kind'] in ('map', 'callbook'):
        fresh = check(source, [asset], {}, checks.settings(), mount)
        if fresh.get('fingerprint') != result.get('fingerprint'):
            raise ValueError('Publisher changed during preparation. Prepare again.')


def recover(value):
    tx = value['transaction']
    mount = Path(tx['mount'])
    if not mount.is_mount(): raise ValueError('Reconnect the library drive to recover this interrupted review')
    backup = mount / '.publisher-review-backups' / value['job']
    configuration_backup = STATE / 'configuration-backups' / value['job']
    for item in tx['files']:
        dest = inside(mount, item['relative_path'])
        saved = backup / item['file']
        if saved.is_file(): shutil.copyfile(saved, dest)
        elif not item['existed']: dest.unlink(missing_ok=True)
    shutil.copyfile(configuration_backup / 'dataark.yaml', ROOT / 'dataark.yaml')
    if (configuration_backup / 'profile').exists(): shutil.copytree(configuration_backup / 'profile', ROOT / 'config/content', dirs_exist_ok=True)
    if 'old_map_config' in value: atomic_write(ROOT / 'deploy/reference/osm-usa.json', json.dumps(value['old_map_config']).encode())
    from tools.library_removal import publish_library
    publish_library(mount)
    value.pop('transaction'); save(value['asset_id'], value)


def apply(value, manifest, asset, mount, installed, source, record, stage):
    from tools.library_removal import serialize, publish_library
    if value['decision'] == 'install':
        for f in value['files']:
            if installed_digest(stage / f['file'],value,'Checking candidate checksum') != f['sha256']: raise ValueError('Prepared candidate no longer matches verification')
        backup = mount / '.publisher-review-backups' / value['job']; backup.mkdir(parents=True)
        # The authoritative manifest may contain private household configuration.
        # Keep its recovery checkpoint off the anonymously served content drive.
        configuration_backup = STATE / 'configuration-backups' / value['job']
        configuration_backup.mkdir(parents=True,mode=0o700);configuration_backup.chmod(0o700)
        shutil.copyfile(ROOT / 'dataark.yaml', configuration_backup / 'dataark.yaml')
        shutil.copyfile(checks.STATE, configuration_backup / 'reference-state.json')
        if (ROOT / 'config/content').is_dir(): shutil.copytree(ROOT / 'config/content', configuration_backup / 'profile')
        if value['kind'] == 'map' and not any(f['file']=='source.json' for f in value['files']):
            metadata = checks.read(ROOT / 'deploy/reference/osm-usa.json', {})
            metadata.update(source=value['edition']['archive_url'],sha256=value['files'][0]['sha256'],bytes=value['files'][0]['bytes'])
            meta=stage/'source.json';meta.write_text(json.dumps(metadata,indent=2))
            value['files'].append({'file':'source.json','relative_path':str(installed.relative_to(mount).parent/'source.json'),'sha256':digest(meta),'bytes':meta.stat().st_size})
        edition = value.get('edition')
        if edition and value['kind'] == 'document':
            new = copy.deepcopy(asset); label = edition['edition']
            new['id'] = asset['id'] + '-edition-' + label
            if any(a['id'] == new['id'] for a in manifest['assets']): raise ValueError('Edition already registered')
            old_label = (record.get('edition_discovery') or {}).get('current_edition', '')
            stem = Path(asset['relative_path']).stem
            stem = stem.replace(old_label, label) if old_label and old_label in stem else stem + '-' + label
            relative = str(Path(asset['relative_path']).with_name(stem + installed.suffix))
            if inside(mount, relative).exists(): raise ValueError('New edition destination already exists')
            new.update(title=asset['title'].replace(old_label, label) if old_label else asset['title'] + ' — ' + label,
                       relative_path=relative, download_url=edition['url'], online_url=edition['url'], expected_hash=value['files'][0]['sha256'], service_endpoint='/library-files/' + relative)
            new['version_pin']=label; new.pop('source_check_url', None)
            manifest['assets'].append(new); value['files'][0]['relative_path'] = relative
        # Preserve acquisition provenance in the collection's own portable records.
        # A new tax year appends a record; it never changes last year's record.
        if value['kind'] == 'document':
            for parent in installed.parents:
                if parent == mount or not parent.is_relative_to(mount): break
                index = parent / 'sources.json'
                if not index.is_file(): continue
                records = json.loads(index.read_text())
                if not isinstance(records, list): continue
                previous = next((r for r in records if r.get('filename') and (parent / r['filename']).resolve() == installed.resolve()), None)
                if not previous: continue
                row = copy.deepcopy(previous)
                if value.get('edition'):
                    row.update(id=row['id'] + '-edition-' + value['edition']['edition'], title=new['title'], url=value['edition']['url'], edition=value['edition']['edition'])
                    records.append(row)
                else:
                    records[records.index(previous)] = row
                    row.setdefault('previous_snapshots', []).append({k: previous.get(k) for k in ('url','sha256','bytes','checked_at','edition')})
                row.update(filename=str(Path(value['files'][0]['relative_path']).relative_to(parent.relative_to(mount))),
                           sha256=value['files'][0]['sha256'], bytes=value['files'][0]['bytes'], status='installed',
                           checked_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
                meta = stage / 'sources.json'; meta.write_text(json.dumps(records, indent=2))
                value['files'].append({'file': meta.name,'relative_path':str(index.relative_to(mount)),'sha256':digest(meta),'bytes':meta.stat().st_size})
                break
        reserve = sum(f['bytes'] for f in value['files']) + 1024**3
        if shutil.disk_usage(mount).free < reserve: raise ValueError('Insufficient free space to retain the previous edition safely')
        replacements = []
        try:
            value['transaction'] = {'mount': str(mount), 'files': []}
            install_phase(value,'Backing up the installed edition')
            for f in value['files']:
                dest = inside(mount, f['relative_path'])
                if dest.is_file(): shutil.copyfile(dest, backup / f['file'])
                value['transaction']['files'].append({**f, 'existed': dest.exists()})
            if value['kind'] == 'map': value['old_map_config'] = checks.read(ROOT / 'deploy/reference/osm-usa.json', {})
            save(asset['id'], value)
            install_phase(value,'Installing verified files')
            for f in value['files']:
                dest = inside(mount, f['relative_path']); dest.parent.mkdir(parents=True, exist_ok=True)
                replacements.append((dest, backup / f['file']))
                temp = dest.with_name(dest.name + '.review-part'); shutil.copyfile(stage / f['file'], temp); temp.chmod(0o644); os.replace(temp, dest)
                for entry in manifest['assets']:
                    if entry['relative_path'] == f['relative_path']: entry['expected_hash'] = f['sha256']
            if value['kind'] == 'map':
                asset['title'] = 'All 50 U.S. states offline street map (' + value['edition']['edition'] + ')'
                metadata = checks.read(ROOT / 'deploy/reference/osm-usa.json', {})
                value['old_map_config'] = metadata
                metadata.update(source=value['edition']['archive_url'], sha256=value['files'][0]['sha256'], bytes=value['files'][0]['bytes'])
                atomic_write(ROOT / 'deploy/reference/osm-usa.json', json.dumps(metadata, indent=2).encode())
            atomic_write(ROOT / 'dataark.yaml', serialize(manifest).encode())
            install_phase(value,'Publishing the library and recovery configuration')
            publish_library(mount)
            subprocess.run([str(ROOT / 'venv/bin/python'), str(ROOT / 'tools/content_profile.py'), 'export'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([str(ROOT / 'venv/bin/python'), str(ROOT / 'tools/content_profile.py'), 'mirror'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        except Exception:
            recover(value)
            raise
    # The acknowledgement belongs to this exact inspected source revision only.
    state = checks.read(checks.STATE, {'sources': {}})
    current = state['sources'].get(source, {})
    if revision(current) != value['revision']: raise ValueError('Publisher check changed during review; prepare again')
    updated = dict(current)
    if value.get('edition'):
        updated.setdefault('edition_discovery', {})['reviewed_candidate'] = value['edition']
        updated['edition_discovery']['candidate'] = None
        updated['edition_discovery']['status'] = 'reviewed'
    updated.update(baseline=value['checked'].get('fingerprint'), fingerprint=value['checked'].get('fingerprint'),
                   fingerprint_kind=value['checked'].get('fingerprint_kind'), pending_change=False, status='unchanged',
                   reviewed_at=time.time(), review_decision=value['decision'],
                   detail='Prepared publisher candidate installed; previous copy retained.' if value['decision'] == 'install' else 'Caretaker reviewed this publisher version and kept the installed edition.')
    state['sources'][source] = updated
    atomic_write(checks.STATE, json.dumps(state, indent=2).encode())
    value.pop('transaction', None)
    if value['decision'] == 'install' and value.get('edition') and value['kind'] == 'document' and record.get('pending_change'):
        updated['pending_change'] = True
        updated['detail'] = 'New edition added. The earlier installed edition also has a publisher change awaiting separate review.'
        state['sources'][source] = updated
        atomic_write(checks.STATE, json.dumps(state, indent=2).encode())
    from tools.update_notifications import content
    content(asset, updated)
    value.update(state='installed' if value['decision'] == 'install' else 'kept', message=updated['detail'])


def worker(asset_id, job):
    from app.services.publisher_review import status
    value = status(asset_id)
    if value.get('job') != job: raise ValueError('Superseded review job')
    try:
        with locked(blocking=True), (checks.STATE.parent / 'worker.lock').open('a') as reference_lock, UPDATES_LOCK.open('a') as content_lock:
            fcntl.flock(reference_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(content_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            manifest, asset, mount, path, source, record = asset_record(asset_id)
            if revision(record) != value['revision'] or file_version(path) != value['installed_version']: raise ValueError('Source changed. Prepare a new comparison.')
            # Staging lives on the content volume, not the small system /tmp.
            stage = STATE / 'payloads' / job if value.get('system_staging') else mount / '.publisher-review' / job
            if value['state'] == 'queued':
                stage.mkdir(parents=True, mode=0o700); stage.chmod(0o700)
                value.update(state='preparing', message='Downloading and verifying a candidate. The installed copy remains available.')
                save(asset_id, value); notify(value)
                if not value.get('installed_hash'): value['installed_hash'] = digest(path)
                prepare(value, asset, mount, path, source, record, stage)
                value.update(state='ready', message='Candidate verified. Review below and choose Install or Keep installed edition.')
            else:
                if installed_digest(path,value,'Checking installed file checksum') != value['installed_hash']: raise ValueError('Installed file changed. Prepare again.')
                apply(value, manifest, asset, mount, path, source, record, stage)
            save(asset_id, value); notify(value)
    except Exception as error:
        if value.get('transaction'):
            try: recover(value)
            except Exception as recovery_error:
                error = RuntimeError(str(error) + '; recovery needs attention: ' + str(recovery_error))
        value.update(state='failed', message=str(error)[:600] + ' Installed copies are retained.'); save(asset_id, value); notify(value)
        raise


if __name__ == '__main__':
    if len(sys.argv) != 3 or not re.fullmatch(r'[a-zA-Z0-9_-]{1,160}', sys.argv[1]) or not re.fullmatch(r'[a-f0-9]{32}', sys.argv[2]): raise SystemExit('Invalid worker identity')
    worker(*sys.argv[1:])
