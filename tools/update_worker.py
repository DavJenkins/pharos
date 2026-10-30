#!/usr/bin/env python3
"""Manifest-driven automatic Kiwix updates; one systemd invocation processes due assets."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import atomic_write, load_manifest
from tools.stage_content_updates import verify
from app.services.library_events import emit

STATE = Path('/var/lib/dataark/updates')
STATUS = STATE / 'status.json'


_reported=None

def report(state, asset=None, percent=None, detail=None):
    global _reported
    bucket=int(percent//10) if type(percent) in (int,float) else None
    marker=(state,asset,bucket)
    if marker!=_reported:
        emit('update_progress',detailed=state not in ('error','waiting','idle'),phase=state,title=asset,reason=detail,percent=percent)
        _reported=marker
    value = {'state': state, 'asset': asset, 'percent': percent, 'detail': detail,
        'updated': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    atomic_write(STATUS, json.dumps(value).encode())
    if detail:
        print(detail, flush=True)


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def interval_seconds(value):
    if value == 'never':
        return None
    match = re.fullmatch(r'([1-9][0-9]*)([smhdw])', value)
    if not match:
        raise ValueError('Invalid refresh interval')
    return int(match[1]) * {'s':1, 'm':60, 'h':3600, 'd':86400, 'w':604800}[match[2]]


def archive_candidate(asset):
    """Route only archive work here; other publishers have their own checker.

    A .zim with a missing/bad recipe must still fail source validation rather
    than silently losing its configured automatic updates.
    """
    spec=asset.get('update_source')
    path=asset.get('relative_path','')
    return (isinstance(spec,dict) and spec.get('kind')=='kiwix_zim') or (isinstance(path,str) and path.lower().endswith('.zim'))


def eligible(asset, checked, now):
    if not archive_candidate(asset):
        return False
    if asset.get('update_policy', 'manual') == 'manual':
        return False
    interval = interval_seconds(asset.get('refresh_interval', 'never'))
    return interval is not None and now - checked >= interval


def source_config(asset):
    spec = asset.get('update_source')
    if not isinstance(spec, dict) or spec.get('kind') != 'kiwix_zim':
        raise ValueError('Automatic updates require an explicit supported update_source (kiwix_zim).')
    directory = spec.get('directory')
    if directory not in ('https://download.kiwix.org/zim/wikipedia/', 'https://download.kiwix.org/zim/stack_exchange/', 'https://download.kiwix.org/zim/ifixit/', 'https://download.kiwix.org/zim/gutenberg/', 'https://download.kiwix.org/zim/other/'):
        raise ValueError('Unsupported Kiwix source directory')
    prefix = spec.get('filename_prefix', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+_', prefix):
        raise ValueError('Unsafe filename prefix')
    if not re.fullmatch(re.escape(prefix) + r'\d{4}-(?:0[1-9]|1[0-2])\.zim', asset['relative_path']):
        raise ValueError('Local archive must be a root-level file in its configured release series.')
    return directory, prefix


def fetch_small(url, limit=12 * 1024 * 1024):
    with urlopen(Request(url, headers={'User-Agent':'DataArk-Updater/1.4'}), timeout=20) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Source metadata exceeded size limit')
    return data


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.names.append(dict(attrs).get('href', ''))


def choose_filename(html, prefix, version_pin=None):
    parser = Links()
    parser.feed(html)
    pattern = re.compile(re.escape(prefix) + r'(\d{4}-(?:0[1-9]|1[0-2]))\.zim')
    matches = [(match[1], name) for name in parser.names if (match := pattern.fullmatch(name))]
    if version_pin:
        matches = [pair for pair in matches if pair[0] == version_pin]
    if not matches:
        raise ValueError('No matching published release (including version pin if set).')
    return max(matches)[1]


def release_info(asset):
    directory, prefix = source_config(asset)
    filename = choose_filename(fetch_small(directory).decode('utf-8'), prefix,
        asset.get('version_pin') if asset.get('update_policy') == 'pin_version' else None)
    # Never replace a newer local release with an older listing unless explicitly pinned.
    if asset.get('update_policy') != 'pin_version' and filename < asset['relative_path']:
        return None
    url = directory + filename
    metalink = ET.fromstring(fetch_small(url + '.meta4'))
    ns = {'m':'urn:ietf:params:xml:ns:metalink'}
    file = metalink.find('m:file', ns)
    if file is None or file.get('name') != filename:
        raise ValueError('Publisher metadata does not match the selected release')
    size = int(file.find('m:size', ns).text)
    sha = file.find('m:hash[@type="sha-256"]', ns).text
    if size <= 0 or not re.fullmatch(r'[0-9a-f]{64}', sha or ''):
        raise ValueError('Invalid publisher size or SHA-256')
    return {'id':asset['id'], 'filename':filename, 'url':url, 'bytes':size, 'sha256':sha}


def child(command, state, title):
    with subprocess.Popen(command, cwd=ROOT) as process:
        try:
            while process.poll() is None:
                report(state, title)
                time.sleep(2)
        except BaseException:
            process.terminate()
            process.wait(timeout=30)
            raise
        if process.returncode:
            raise RuntimeError('Update subprocess failed; see journalctl -u dataark-update.service')


def download(item, staging, title):
    final = staging / item['filename']
    partial = staging / (item['filename'] + '.part')
    for path in (final, partial):
        if path.is_symlink():
            raise ValueError('Refusing a symlink in download staging')
    if not final.exists():
        remaining = item['bytes'] - (partial.stat().st_size if partial.exists() else 0)
        if remaining < 0:
            raise ValueError('Partial download is larger than the selected release')
        if shutil.disk_usage(staging).free < remaining + 2 * 1024**3:
            raise RuntimeError('Insufficient SSD space; current archives have not been removed.')
        if remaining:
            command = ['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                '--retry', '2', '--retry-delay', '10', '--connect-timeout', '20', '--speed-time', '120',
                '--speed-limit', '1024', '--silent', '--show-error', '--continue-at', '-', '--output', str(partial), item['url']]
            with subprocess.Popen(command) as process:
                try:
                    while process.poll() is None:
                        size = partial.stat().st_size if partial.exists() else 0
                        report('downloading', title, round(min(100, size * 100 / item['bytes']), 1))
                        time.sleep(2)
                except BaseException:
                    process.terminate()
                    process.wait(timeout=30)
                    raise
                if process.returncode:
                    # curl 18 = partial transfer; network errors can resume at the next run.
                    if process.returncode in (5, 6, 7, 18, 28, 35, 52, 55, 56):
                        raise URLError('Download interrupted; partial data retained for automatic resume.')
                    raise RuntimeError(f'Download failed with curl status {process.returncode}; partial file retained.')
        final = partial
    report('verifying', title)
    last = [0.0]
    def progress(done, total):
        if time.monotonic() - last[0] >= 2:
            report('verifying', title, round(done * 100 / total, 1))
            last[0] = time.monotonic()
    verify(final, item, progress=progress)
    if final == partial:
        partial.rename(staging / item['filename'])


def run():
    from tools.library_removal import recover
    recover()
    manifest_snapshot[0] = (ROOT / 'dataark.yaml').read_text(encoding='utf-8')
    data = load_manifest(ROOT / 'dataark.yaml')
    if data['system']['base_mount'] != '/mnt/storage':
        raise ValueError('This Kiwix deployment requires base_mount /mnt/storage.')
    root = Path('/mnt/storage')
    if not root.is_mount():
        report('waiting', detail='Waiting for the content SSD to be mounted.')
        return
    if shutil.which('curl') is None:
        raise RuntimeError('curl is required')
    staging = root / '.dataark-updates'
    if staging.is_symlink():
        raise ValueError('Staging directory cannot be a symlink')
    staging.mkdir(exist_ok=True)
    history = read_json(STATE / 'checked.json', {})
    journal = staging / 'activation.json'
    if journal.exists():
        state = read_json(journal, {})
        command = [sys.executable, str(ROOT / 'tools/activate_content_updates.py')]
        if state.get('phase') != 'committed':
            command.append('--rollback')
        child(command, 'recovering', 'Previous interrupted update')
        report('idle')
        return
    enabled = {r['id'] for r in data['repositories'] if r.get('enabled', True)}
    import fcntl
    checked_any = False
    for asset in data['assets']:
        if asset.get('removed') or asset['repository_id'] not in enabled or not eligible(asset, history.get(asset['id'], 0), time.time()):
            continue
        checked_any = True
        report('checking', asset['title'])
        item = release_info(asset)
        if item is not None and (asset['relative_path'] != item['filename'] or not (root / item['filename']).is_file()):
            lockpath = staging / '.lock'
            if lockpath.is_symlink():
                raise ValueError('Download lock cannot be a symlink')
            with lockpath.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                download(item, staging, asset['title'])
            plan = STATE / 'pending-plan.json'
            atomic_write(plan, json.dumps({'archives':[item]}).encode())
            if (ROOT / 'dataark.yaml').read_text(encoding='utf-8') != manifest_snapshot[0]:
                raise RuntimeError('Manifest changed during the download; retrying with fresh configuration next run.')
            child([sys.executable, str(ROOT / 'tools/activate_content_updates.py'), '--plan', str(plan)], 'activating', asset['title'])
            emit('archive_activated',asset_id=asset['id'],title=asset['title'])
            manifest_snapshot[0] = (ROOT / 'dataark.yaml').read_text(encoding='utf-8')
        history[asset['id']] = time.time()
        atomic_write(STATE / 'checked.json', json.dumps(history).encode())
    if checked_any:
        child([sys.executable, str(ROOT / 'tools/check_upstream.py')], 'checking', 'Online source status')
        child(['bash', str(ROOT / 'deploy/deploy-web.sh')], 'publishing', 'Dashboard')
    report('idle')


manifest_snapshot = [None]

def main():
    STATE.mkdir(parents=True, exist_ok=True)
    import fcntl
    with (STATE / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        try:
            manifest_snapshot[0] = (ROOT / 'dataark.yaml').read_text(encoding='utf-8')
            run()
        except BlockingIOError:
            report('waiting', detail='Another content operation holds the download lock.')
        except (URLError, TimeoutError, ConnectionError) as error:
            report('waiting', detail=str(error))
        except Exception as error:
            report('error', detail=str(error))
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
