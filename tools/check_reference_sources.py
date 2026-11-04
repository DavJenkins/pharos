#!/usr/bin/env python3
"""Bounded weekly publisher checks. Never changes an installed library file."""
import fcntl
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import ssl
import argparse
import time
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, quote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import load_manifest, inside, atomic_write
from app.services.reference_checks import settings, source, read, STATE
from tools.update_worker import interval_seconds

def failure_detail(error):
    if isinstance(error, HTTPError):
        message = {403: 'Publisher refused this check', 404: 'Recorded publisher URL was not found',
                   429: 'Publisher asked us to slow down'}.get(error.code, 'Publisher request failed')
        return message + ' (HTTP ' + str(error.code) + '). Installed copy retained.'
    if 'CERTIFICATE_VERIFY_FAILED' in str(error):
        return 'Publisher TLS certificate could not be verified. Installed copy retained.'
    return str(error)[:500]

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, value):
        if not self.hidden: self.parts.append(value)

def body_fingerprint(data, content_type, url):
    if 'html' in content_type or data.lstrip().lower().startswith((b'<!doctype html', b'<html')):
        # This publisher delivers the provisions in Nuxt data, while visible
        # page furniture changes independently of the constitutional text.
        if urlsplit(url).hostname == '50constitutions.org':
            from tools.install_jurisdictions import university_body
            body, _, _, _ = university_body(data.decode('utf-8'))
            parser = Text(); parser.feed(body)
            text = ' '.join(' '.join(parser.parts).split())
            return hashlib.sha256(text.encode()).hexdigest(), 'constitutional-text-v1'
        if urlsplit(url).hostname in {'www.energy.gov', 'malegislature.gov', 'www.leg.state.fl.us', 'cnmilaw.gov', 'law.lis.virginia.gov'}:
            # Match the substantive-body extractor used to make these saved
            # snapshots, excluding menus, scripts, forms and other furniture.
            from tools.install_resilience import body_copy
            body, _ = body_copy(data, url)
            parser = Text(); parser.feed(body)
            text = ' '.join(' '.join(parser.parts).split())
            return hashlib.sha256(text.encode()).hexdigest(), 'publisher-body-v1'
        parser = Text(); parser.feed(data.decode('utf-8', errors='replace'))
        text = ' '.join(' '.join(parser.parts).split())
        if len(text) < 100 or re.search(r'^(access denied|just a moment|verify you are human)', text, re.I):
            raise ValueError('Publisher returned an access/challenge page or incomplete HTML')
        return hashlib.sha256(text.encode()).hexdigest(), 'text'
    if data.startswith(b'%PDF-'):
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(data); f.flush()
            subprocess.run(['pdfinfo', f.name], check=True, timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    elif urlsplit(url).path.lower().endswith('.docx'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if 'word/document.xml' not in archive.namelist() or any('vbaproject' in n.lower() for n in archive.namelist()):
                raise ValueError('Invalid or macro-enabled Word document')
    elif 'html' in content_type:
        raise ValueError('Unexpected HTML response')
    return hashlib.sha256(data).hexdigest(), 'bytes'


def retired_map_edition(url, assets, previous, config, opener=urlopen, today=None):
    """Discover a retained daily map build without downloading a planet archive.

    The installed extraction and its pinned source provenance are unchanged.
    A new build needs a separate, verified regional extraction before activation.
    """
    match = re.fullmatch(r'https://build\.protomaps\.com/(\d{8})\.pmtiles', url)
    if not match or not assets or not all(Path(a['relative_path']).suffix == '.pmtiles' for a in assets):
        raise ValueError('Not a supported dated map extraction source')
    installed = datetime.strptime(match[1], '%Y%m%d').date()
    today = today or datetime.now(timezone.utc).date()
    for offset in range(4):
        day = today - timedelta(days=offset)
        if day <= installed: continue
        candidate_url = 'https://build.protomaps.com/' + day.strftime('%Y%m%d') + '.pmtiles'
        try:
            with opener(Request(candidate_url, headers={'User-Agent':'DataArk bounded map edition check', 'Range':'bytes=0-126', 'Accept-Encoding':'identity'}), timeout=min(config.get('timeout_seconds',45),15)) as response:
                if response.url != candidate_url or response.status != 206:
                    raise ValueError('Map publisher did not return the requested bounded header')
                length = re.fullmatch(r'bytes 0-126/(\d+)', response.headers.get('Content-Range',''))
                header = response.read(127)
                if not length or len(header) != 127 or header[:8] != b'PMTiles\x03':
                    raise ValueError('New map build has an invalid PMTiles header')
                candidate = {'edition':day.isoformat(), 'url':'https://maps.protomaps.com/builds/',
                             'archive_url':candidate_url, 'bytes':int(length[1]),
                             'etag':response.headers.get('ETag'), 'kind':'map_extraction'}
            detail = 'New Protomaps build '+day.isoformat()+' is available. Rebuild and verify the configured regional extraction before activation; installed map retained.'
            if previous.get('edition_discovery',{}).get('reviewed_candidate') == candidate:
                return dict(previous,status='unchanged',pending_change=False,detail='Caretaker reviewed this map build and kept the installed map.')
            return dict(previous, status='changed', pending_change=True, detail=detail,
                        fingerprint=candidate_url+'|'+str(candidate['etag']), fingerprint_kind='map-edition-v1',
                        edition_discovery={'status':'available','candidate':candidate,'detail':detail,'attempted_at':time.time()})
        except HTTPError as error:
            if error.code != 404: raise
    raise ValueError('Pinned map build expired; no retained build found in the bounded four-day window. Installed map retained.')

def check(url, assets, previous, config, root, opener=urlopen):
    if urlsplit(url).scheme != 'https':
        raise ValueError('Only explicit HTTPS publisher sources are checked')
    # Publisher filenames can contain Unicode. Encode their UTF-8 bytes for
    # HTTP without changing existing escapes, separators or the state key.
    request_url = quote(url, safe=":/?#[]@!$&'()*+,;=%")
    metadata_only = any(urlsplit(url).path.lower().endswith(ext) for ext in ('.zip', '.pmtiles')) or any(a.get('repository_id') == 'curriculum' for a in assets)
    headers = {'User-Agent': 'Mozilla/5.0 (DataArk offline reference source check)'}
    semantic_hosts = {'50constitutions.org', 'www.energy.gov', 'malegislature.gov', 'www.leg.state.fl.us', 'cnmilaw.gov', 'law.lis.virginia.gov'}
    migrate_text = urlsplit(url).hostname in semantic_hosts and previous.get('fingerprint_kind') not in {'constitutional-text-v1', 'publisher-body-v1'}
    if previous.get('etag') and not migrate_text: headers['If-None-Match'] = previous['etag']
    elif previous.get('last_modified') and not migrate_text: headers['If-Modified-Since'] = previous['last_modified']
    from tools.source_tls import extra_ca, context
    options = {'timeout': config.get('timeout_seconds', 45)}
    if extra_ca(url, ROOT):
        options['context'] = context(url, ROOT)
    try:
        try:
            response = opener(Request(request_url, headers=headers, method='HEAD' if metadata_only else 'GET'), **options)
        except HTTPError as error:
            if not metadata_only or error.code not in (403, 405, 501): raise
            # Some public package hosts (including FCC) refuse HEAD. Ask for
            # one byte, inspect headers, then close without reading the body.
            response = opener(Request(request_url, headers={**headers, 'Range': 'bytes=0-0'}, method='GET'), **options)
    except HTTPError as error:
        if error.code == 304:
            return dict(previous, status='changed' if previous.get('pending_change') else 'unchanged', detail='Publisher confirms the previously checked version.')
        if error.code == 404 and re.fullmatch(r'https://build\.protomaps\.com/\d{8}\.pmtiles',url):
            return retired_map_edition(url, assets, previous, config, opener)
        raise
    with response:
        if urlsplit(response.url).scheme != 'https': raise ValueError('Publisher redirected away from HTTPS')
        result = {'etag': response.headers.get('ETag'), 'last_modified': response.headers.get('Last-Modified')}
        if metadata_only:
            if 'html' in response.headers.get('Content-Type', '').lower():
                raise ValueError('Publisher returned an HTML page instead of package metadata')
            length = response.headers.get('Content-Length', '')
            content_range = response.headers.get('Content-Range', '')
            match = re.fullmatch(r'bytes 0-0/(\d+)', content_range)
            if match: length = match[1]
            fingerprint = '|'.join([response.headers.get('ETag', ''), response.headers.get('Last-Modified', ''), length])
            if fingerprint == '||':
                return dict(result, status='reachable', detail='Source reachable; publisher provides no version metadata. Package needs collection-specific review.', pending_change=previous.get('pending_change', False))
            kind = 'metadata'
        else:
            limit = config.get('max_bytes', 64 * 1024**2)
            length = response.headers.get('Content-Length')
            if length and int(length) > limit: raise ValueError('Source exceeds the bounded check size; collection-specific check required')
            data = response.read(limit + 1)
            if len(data) > limit: raise ValueError('Source exceeds the bounded check size')
            expected_suffix = Path(assets[0]['relative_path']).suffix.lower() if not assets[0].get('source_check_url') else ''
            if expected_suffix == '.pdf' and not data.startswith(b'%PDF-'):
                raise ValueError('Publisher did not return a PDF; current copy retained')
            if expected_suffix == '.docx':
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if 'word/document.xml' not in archive.namelist() or any('vbaproject' in n.lower() for n in archive.namelist()):
                        raise ValueError('Invalid or macro-enabled Word document')
            fingerprint, kind = body_fingerprint(data, response.headers.get('Content-Type', ''), url)
    baseline = previous.get('baseline')
    if kind in {'constitutional-text-v1', 'publisher-body-v1'} and previous.get('fingerprint_kind') != kind:
        # Migrate an older page-furniture baseline only when the freshly
        # retrieved provisions exactly match every installed snapshot.
        matches = []
        for asset in assets:
            try:
                snapshot = inside(root, asset['relative_path']).read_text(encoding='utf-8')
                if kind == 'constitutional-text-v1':
                    start = snapshot.find('<h2>')
                    if start < 0 or 'class="constitutional-provision"' not in snapshot:
                        raise ValueError('Installed constitutional provisions not identified')
                else:
                    boundary = re.search(r'Original publisher page \(internet\)</a></div>|Publisher source</a></p>', snapshot)
                    if not boundary: raise ValueError('Installed publisher-body boundary not identified')
                    start = boundary.end()
                parser = Text(); parser.feed(snapshot[start:])
                text = ' '.join(' '.join(parser.parts).split())
                matches.append(hashlib.sha256(text.encode()).hexdigest() == fingerprint)
            except (OSError, UnicodeError, ValueError):
                matches.append(False)
        if matches and all(matches):
            baseline = fingerprint
    # Byte-identical direct files can be compared with the installed copy immediately.
    if not baseline and kind == 'bytes':
        direct = [a for a in assets if not a.get('source_check_url') and Path(a['relative_path']).suffix.lower() in ('.pdf', '.docx', '.json', '.txt')]
        baseline = next((a.get('expected_hash') for a in direct if a.get('expected_hash')), None)
    changed = bool(baseline and fingerprint != baseline)
    result.update(fingerprint=fingerprint, fingerprint_kind=kind, baseline=baseline or fingerprint, pending_change=changed,
                  status='changed' if changed else 'unchanged' if baseline else 'baseline',
                  detail='Publisher source changed; installed copy retained for review.' if changed else
                         'Recorded source matches the installed file or previous baseline.' if baseline else
                         'First publisher baseline recorded; saved snapshot freshness is not established.')
    return result

def discover_editions(manifest, root, state, config, retry_errors=False):
    from tools.edition_discovery import discover
    catalogue=read(ROOT/'deploy/reference/edition-discovery.json', {})
    if not catalogue.get('enabled'):return
    if catalogue.get('schema')!=1:raise ValueError('Unsupported edition discovery schema')
    interval=interval_seconds(catalogue.get('interval','7d'))
    enabled={r['id'] for r in manifest['repositories'] if r.get('enabled',True)}
    for asset in manifest['assets']:
        rule=catalogue.get('rules',{}).get(asset['id'])
        url=source(asset)
        if not rule or not url or asset.get('removed') or asset['repository_id'] not in enabled or not inside(root,asset['relative_path']).is_file():continue
        record=state.setdefault('sources',{}).setdefault(url,{})
        previous=record.get('edition_discovery',{})
        if time.time()-previous.get('attempted_at',0)<interval and not (retry_errors and previous.get('status')=='error'):continue
        try:
            result=discover(rule,asset)
            if previous.get('reviewed_candidate'):
                result['reviewed_candidate']=previous['reviewed_candidate']
                if result.get('candidate')==previous['reviewed_candidate']:
                    result.update(status='reviewed',candidate=None,detail='Caretaker already reviewed this edition; installed editions retained.')
            if result['status']=='error' and previous.get('candidate'):result['candidate']=previous['candidate']
        except Exception as error:
            result={**previous,'status':'error','detail':'Edition discovery failed; installed copy retained.','issues':[failure_detail(error)]}
        result['attempted_at']=time.time();record['edition_discovery']=result
        atomic_write(STATE,(json.dumps(state,indent=2)+'\n').encode())
        from tools.update_notifications import content
        content(asset,record)
        print('edition',asset['id'],result['status'],flush=True)
        time.sleep(config.get('request_delay_seconds',1))


def run(retry_errors=False):
    config = settings()
    if not config.get('enabled'): return
    manifest = load_manifest(ROOT / 'dataark.yaml')
    root = Path(manifest['system']['base_mount'])
    if not root.is_mount(): raise RuntimeError('Content SSD is not mounted')
    enabled = {r['id'] for r in manifest['repositories'] if r.get('enabled', True)}
    groups = {}
    for asset in manifest['assets']:
        url = source(asset)
        if url and not asset.get('removed') and asset['repository_id'] in enabled and inside(root, asset['relative_path']).is_file():
            groups.setdefault(url, []).append(asset)
    state = read(STATE, {'sources': {}})
    discover_editions(manifest,root,state,config,retry_errors)
    for url, assets in groups.items():
        previous = state.setdefault('sources', {}).get(url, {})
        if not (retry_errors and previous.get('status') == 'error') and time.time() - previous.get('attempted_at', 0) < interval_seconds(config.get('interval', '7d')): continue
        attempted = time.time()
        try:
            result = check(url, assets, previous, config, root)
            result['checked_at'] = time.time()
        except Exception as error:
            result = dict(previous, status='error', detail=failure_detail(error))
        if previous.get('edition_discovery') and not result.get('edition_discovery'):result['edition_discovery']=previous['edition_discovery']
        result['attempted_at'] = attempted
        state['sources'][url] = result
        atomic_write(STATE, (json.dumps(state, indent=2) + '\n').encode())
        from tools.update_notifications import content
        for asset in assets:content(asset,result)
        print(result['status'], ','.join(a['id'] for a in assets), result.get('detail', ''), flush=True)
        time.sleep(config.get('request_delay_seconds', 1))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retry-errors', action='store_true', help='Retry failed checks once without repeating completed checks')
    args = parser.parse_args()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with (STATE.parent / 'worker.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Publisher checks deferred: another content review owns the source lock.', flush=True)
            raise SystemExit(0)
        run(retry_errors=args.retry_errors)
