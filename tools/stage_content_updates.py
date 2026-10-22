#!/usr/bin/env python3
"""Stage the reviewed archive update plan on the Pi; leave the live library intact."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate_plan(plan):
    items = plan['archives']
    names = set()
    for item in items:
        name = item['filename']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.zim', name) or name in names:
            raise ValueError('Unsafe or duplicate archive filename')
        names.add(name)
        if type(item['bytes']) is not int or item['bytes'] <= 0:
            raise ValueError('Invalid archive size')
        if not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid publisher SHA-256')
        url = urlsplit(item['url'])
        if url.scheme != 'https' or url.netloc != 'download.kiwix.org' or url.query or url.fragment or url.path not in ('/zim/wikipedia/' + name, '/zim/stack_exchange/' + name, '/zim/ifixit/' + name, '/zim/gutenberg/' + name):
            raise ValueError('Unexpected archive source')
    return items


def verify(path, item, progress=None):
    if path.is_symlink() or path.stat().st_size != item['bytes']:
        raise ValueError('Downloaded size mismatch: ' + item['filename'])
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        if stream.read(4) != b'ZIM\x04':
            raise ValueError('Not a ZIM archive: ' + item['filename'])
        stream.seek(0)
        done = 0
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
            done += len(block)
            if progress:
                progress(done, item['bytes'])
    if digest.hexdigest() != item['sha256']:
        raise ValueError('SHA-256 mismatch; staged file retained for inspection: ' + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT / 'deploy/content-update-plan.json')
    args = parser.parse_args()
    items = validate_plan(json.loads(args.plan.read_text(encoding='utf-8')))
    root = Path('/mnt/storage')
    if not root.is_mount():
        raise RuntimeError('SSD is not mounted; refusing to use the SD card.')
    if shutil.which('curl') is None:
        raise RuntimeError('curl is required; install it before staging downloads.')
    staging = root / '.dataark-updates'
    if staging.is_symlink():
        raise RuntimeError('Staging directory cannot be a symlink.')
    staging.mkdir(exist_ok=True)
    import fcntl
    lockpath = staging / '.lock'
    if lockpath.is_symlink():
        raise RuntimeError('Lock cannot be a symlink.')
    with lockpath.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        remaining = 0
        for item in items:
            complete = staging / item['filename']
            partial = staging / (item['filename'] + '.part')
            if complete.is_symlink() or partial.is_symlink():
                raise RuntimeError('Staged files cannot be symlinks.')
            if not complete.exists():
                remaining += max(0, item['bytes'] - (partial.stat().st_size if partial.exists() else 0))
        free = shutil.disk_usage(root).free
        if free < remaining + 2 * 1024**3:
            raise RuntimeError('Insufficient SSD space for staged downloads plus 2 GiB reserve.')
        print(f'Need {remaining / 1024**3:.2f} GiB additional space; {free / 1024**3:.2f} GiB free.', flush=True)
        print('Only NEW downloads are checksummed. Existing archives are untouched.', flush=True)
        for item in items:
            complete = staging / item['filename']
            partial = staging / (item['filename'] + '.part')
            print('\nPreparing ' + item['filename'], flush=True)
            if complete.exists():
                verify(complete, item)
                print('Already staged and verified.', flush=True)
                continue
            if not partial.exists() or partial.stat().st_size < item['bytes']:
                subprocess.run(['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                    '--retry', '5', '--retry-delay', '10', '--connect-timeout', '30',
                    '--speed-time', '120', '--speed-limit', '1024', '--continue-at', '-',
                    '--output', str(partial), item['url']], check=True)
            print('Validating downloaded size, ZIM header, and publisher SHA-256...', flush=True)
            verify(partial, item)
            partial.rename(complete)
            print('Verified and staged.', flush=True)
        print('\nAll five replacements are staged in /mnt/storage/.dataark-updates.', flush=True)
        print('No live archives, manifest entries, or Kiwix configuration were changed.', flush=True)
        print('The next step is Kiwix registration, switch-over verification, and removal of old versions.', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Update staging stopped: {error}', file=sys.stderr)
        raise SystemExit(1)