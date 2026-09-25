#!/usr/bin/env python3
"""Activate verified staged ZIM updates, reload Kiwix, then retire old versions."""
import argparse
import calendar
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import atomic_write, load_manifest
from tools.stage_content_updates import validate_plan, verify
from tools.publish_content import publish


def docker(*args):
    command = ([] if os.geteuid() == 0 else ['sudo']) + ['docker', *args]
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=120).stdout


def check_container(root):
    container = json.loads(docker('inspect', 'kiwix-serve'))[0]
    if container['Config'].get('Cmd') != ['*.zim']:
        raise RuntimeError('Kiwix arguments changed; this updater requires the reviewed *.zim configuration.')
    if container['Config'].get('Entrypoint') != ['/usr/bin/dumb-init', '--', '/usr/local/bin/start.sh']:
        raise RuntimeError('Unexpected Kiwix entrypoint; review before changing content.')
    if not any(m.get('Destination') == '/data' and Path(m.get('Source', '')).resolve() == root for m in container['Mounts']):
        raise RuntimeError('Kiwix does not mount this SSD at /data.')
    return bool(container['State']['Running'])


def replacement_manifest(original, items):
    text = original
    for item in items:
        pattern = r'(?ms)^  - id: ' + re.escape(item['id']) + r'\n.*?(?=^  - id: |\Z)'
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise ValueError('Expected one manifest asset: ' + item['id'])
        match = matches[0]
        block = match.group()
        if '    repository_id:' not in block:
            raise ValueError('Matched record is not an asset.')
        for field, value in [('relative_path', item['filename']), ('download_url', item['url'])]:
            block, count = re.subn(r'^    ' + field + r':.*$', '    ' + field + ': ' + value, block, flags=re.M)
            if count != 1:
                raise ValueError('Missing or repeated ' + field)
        block = re.sub(r'^    (?:mirror_url|expected_hash):.*\n', '', block, flags=re.M)
        block = block.replace('    download_url: ' + item['url'] + '\n',
            '    download_url: ' + item['url'] + '\n    expected_hash: "' + item['sha256'] + '"\n')
        date = re.search(r'_(\d{4})-(\d{2})\.zim$', item['filename'])
        if date:
            label = calendar.month_name[int(date[2])] + ' ' + date[1]
            block = re.sub(r'(^    title:.*)\([A-Za-z]+ \d{4}\)', lambda m: m[1] + '(' + label + ')', block, flags=re.M)
        text = text[:match.start()] + block + text[match.end():]
    return text.replace('# Exact-version sources checked 2026-09-24; unavailable versions remain preserved locally.',
        '# Old versions are retired after replacement downloads and Kiwix activation are verified.')


def archive_names(xml):
    root = ET.fromstring(xml)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    return {unquote(urlsplit(link.attrib.get('href', '')).path).rsplit('/', 1)[-1]
        for link in root.findall('a:entry/a:link', ns) if link.attrib.get('type') == 'text/html'}


def wait_for_library(items, old_names, port):
    expected = {Path(item['filename']).stem for item in items}
    previous = {Path(name).stem for name in old_names}
    last = 'No response'
    for _ in range(30):
        try:
            with urlopen(f'http://127.0.0.1:{port}/catalog/v2/entries?count=-1', timeout=5) as response:
                names = archive_names(response.read(4 * 1024 * 1024))
            if expected <= names and not previous.intersection(names):
                return
            last = 'Expected replacement archives are not all in the catalog yet.'
        except (OSError, ValueError, ET.ParseError) as error:
            last = str(error)
        time.sleep(2)
    raise RuntimeError('Kiwix did not confirm the replacement library: ' + last)


def switch_files(root, staging, previous, records):
    for record in records:
        if record['old']:
            (root / record['old']).rename(previous / record['old'])
        (staging / record['new']).rename(root / record['new'])


def restore_files(root, staging, previous, records):
    # Handles interruption after either rename, without overwriting any file.
    for record in reversed(records):
        live_new = root / record['new']
        staged_new = staging / record['new']
        saved_old = previous / record['old'] if record['old'] else None
        live_old = root / record['old'] if record['old'] else None
        if live_new.exists():
            if staged_new.exists():
                raise RuntimeError('Both live and staged replacements exist; refusing overwrite.')
            live_new.rename(staged_new)
        if saved_old is not None and saved_old.exists():
            if live_old.exists():
                raise RuntimeError('Both live and saved old archives exist; refusing overwrite.')
            saved_old.rename(live_old)


def validate_records(records):
    names = []
    for record in records:
        for key in ('old', 'new'):
            name = record[key]
            if key == 'old' and name is None:
                continue
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.zim', name):
                raise ValueError('Unsafe activation record')
            names.append(name)
    if len(set(names)) != len(names):
        raise ValueError('Overlapping activation records')


def finish(root, previous, journal, state):
    print('Publishing updated portable catalog and dashboard...', flush=True)
    publish(root)
    subprocess.run(['bash', str(ROOT / 'deploy/deploy-web.sh')], cwd=ROOT, check=True)
    # Deletion happens only after Kiwix, the manifest and published website have switched.
    for record in state['records']:
        if record['old'] is None:
            continue
        old = previous / record['old']
        if old.is_symlink():
            raise RuntimeError('Refusing to delete a symlink.')
        old.unlink(missing_ok=True)
    journal.unlink()
    print('Update complete: replacements active; superseded archives removed.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT / 'deploy/content-update-plan.json')
    parser.add_argument('--rollback', action='store_true', help='Recover an interrupted, uncommitted switch.')
    args = parser.parse_args()
    root = Path('/mnt/storage').resolve()
    if not root.is_mount():
        raise RuntimeError('SSD is not mounted.')
    staging = root / '.dataark-updates'
    previous = staging / 'previous'
    journal = staging / 'activation.json'
    manifest = ROOT / 'dataark.yaml'
    for path in (staging, previous, journal, staging / '.lock', manifest):
        if path.is_symlink():
            raise RuntimeError('Refusing symlink: ' + str(path))
    if not staging.is_dir():
        raise RuntimeError('No staged downloads. Run tools/stage_content_updates.py first.')
    import fcntl
    with (staging / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if journal.exists():
            state = json.loads(journal.read_text())
            validate_records(state['records'])
            if state['phase'] == 'committed':
                if args.rollback:
                    raise RuntimeError('Committed update cannot be rolled back after cleanup has begun.')
                wait_for_library(state['items'], [r['old'] for r in state['records'] if r['old']], state['port'])
                finish(root, previous, journal, state)
                return 0
            if not args.rollback:
                raise RuntimeError('Interrupted switch: run this command with --rollback first.')
            docker('stop', 'kiwix-serve')
            restore_files(root, staging, previous, state['records'])
            atomic_write(manifest, state['original'].encode('utf-8'))
            if state.get('was_running', True):
                docker('start', 'kiwix-serve')
            journal.unlink()
            print('Previous files and manifest restored. Staged replacements retained.')
            return 0
        if args.rollback:
            raise RuntimeError('No interrupted switch to roll back.')
        items = validate_plan(json.loads(args.plan.read_text()))
        data = load_manifest(manifest)
        assets = {asset['id']: asset for asset in data['assets']}
        if all(assets[item['id']]['relative_path'] == item['filename'] and (root / item['filename']).is_file() for item in items):
            wait_for_library(items, [], data['system']['services']['kiwix_port'])
            print('Manifest and Kiwix already use the planned replacements.')
            return 0
        records = [{'old': assets[item['id']]['relative_path'] if (root / assets[item['id']]['relative_path']).exists() else None, 'new': item['filename']} for item in items]
        validate_records(records)
        for record in records:
            paths = [staging / record['new']] + ([root / record['old']] if record['old'] else [])
            for path in paths:
                if path.is_symlink() or not path.is_file():
                    raise RuntimeError('Missing file or symlink: ' + str(path))
            if (root / record['new']).exists() or (record['old'] and (previous / record['old']).exists()):
                raise RuntimeError('Destination already exists; refusing to overwrite.')
        was_running = check_container(root)
        original = manifest.read_text(encoding='utf-8')
        updated = replacement_manifest(original, items)
        candidate = staging / 'candidate-manifest.yaml'
        atomic_write(candidate, updated.encode('utf-8'))
        load_manifest(candidate)
        for item in items:
            print('Verifying staged replacement: ' + item['filename'], flush=True)
            verify(staging / item['filename'], item)
        if manifest.read_text(encoding='utf-8') != original:
            raise RuntimeError('Manifest changed during verification; restart the activation.')
        previous.mkdir(exist_ok=True)
        state = {'phase': 'prepared', 'records': records, 'original': original, 'items': items, 'was_running': was_running,
            'port': data['system']['services']['kiwix_port']}
        atomic_write(journal, json.dumps(state).encode())
        try:
            docker('stop', 'kiwix-serve')
            switch_files(root, staging, previous, records)
            docker('start', 'kiwix-serve')
            wait_for_library(items, [record['old'] for record in records if record['old']], state['port'])
            atomic_write(manifest, updated.encode('utf-8'))
            state['phase'] = 'committed'
            atomic_write(journal, json.dumps(state).encode())
        except Exception:
            print('Activation failed. Restoring the previous library...', flush=True)
            docker('stop', 'kiwix-serve')
            restore_files(root, staging, previous, records)
            atomic_write(manifest, original.encode('utf-8'))
            if was_running:
                docker('start', 'kiwix-serve')
            journal.unlink()
            raise
        finish(root, previous, journal, state)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Activation stopped: {error}', file=sys.stderr)
        print('If already committed, rerun to finish publishing and cleanup. Otherwise follow the rollback instruction above.', file=sys.stderr)
        raise SystemExit(1)