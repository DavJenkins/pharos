"""Capacity-aware file cloning of a mounted public content volume.

Planning is read-only. Applying requires local root and the exact reviewed plan.
No formatting, deletion, credential copying, or download operations are defined.
"""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/mnt/storage')
STATUS = Path('/var/lib/dataark/cloning')
MARKER = '.dataark-clone'
GENERATOR = 'dataark-drive-clone-v1'
FILESYSTEMS = {'ext4', 'exfat', 'ntfs', 'ntfs3', 'fuseblk'}
SYSTEM_METADATA = {'System Volume Information', '$RECYCLE.BIN', 'lost+found'}
SECRET_NAMES = {'credentials.json', 'secrets.yaml', 'secrets.yml', 'id_rsa',
                'id_ed25519', 'authorized_keys'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2 * 1024**2), b''):
            result.update(block)
    return result.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    if temporary.is_symlink() or path.is_symlink():
        raise ValueError('Unexpected metadata symlink')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o644)
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def command_json(arguments):
    return json.loads(subprocess.check_output(arguments, text=True, timeout=15))


def storage():
    mounts = command_json(['findmnt', '--json', '--list', '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID'])
    blocks = command_json(['lsblk', '--json', '--bytes', '--paths', '--output',
                           'PATH,NAME,PKNAME,TYPE,MODEL,SERIAL,SIZE,FSTYPE,UUID,TRAN'])
    devices = {}
    def visit(items, parent=None):
        for original in items:
            item = dict(original)
            path = item.get('path') or item['name']
            item['parent'] = item.get('pkname') or parent
            devices[path] = item
            visit(item.get('children', []), path)
    visit(blocks['blockdevices'])
    return {item['target']: item for item in mounts['filesystems']}, devices


def device_path(source):
    return str(Path(source.split('[')[0]).resolve())


def backing_disks(source, devices):
    path = device_path(source)
    visited = set()
    while path in devices and path not in visited:
        visited.add(path)
        item = devices[path]
        if item['type'] in {'disk', 'loop'}:
            return {path}
        parent = item.get('parent')
        if not parent:
            break
        path = str(Path(parent).resolve())
    raise ValueError('Cannot establish the backing disk identity')


def journal_path(target):
    primary = Path(target)/MARKER
    return primary if primary.exists() else Path(target)/'.dataark-clone-initializing'


def inspect_target(target, mounts=None, devices=None):
    target = Path(target).resolve()
    if mounts is None or devices is None:
        mounts, devices = storage()
    result = {'path': str(target), 'eligible': False, 'reasons': []}
    row = mounts.get(str(target))
    if row is None or not target.is_mount():
        result['reasons'].append('Choose the root of a separately mounted local drive.')
        return result
    block = devices.get(device_path(row['source']), {})
    uuid = row.get('uuid') or block.get('uuid')
    result.update(device=row['source'], filesystem=block.get('fstype') or row['fstype'],
                  uuid=uuid, model=block.get('model') or '', serial=block.get('serial') or '',
                  size_bytes=block.get('size') or 0, read_only='ro' in row['options'].split(','))
    try:
        if str(SOURCE) not in mounts:
            raise ValueError('The original content drive is not mounted.')
        protected = set()
        for name in ('/', '/boot', '/boot/firmware', '/usr', '/var', '/home', str(SOURCE)):
            if name in mounts:
                protected |= backing_disks(mounts[name]['source'], devices)
        if backing_disks(row['source'], devices) & protected:
            raise ValueError('This is a system/content disk or another partition on one of those disks.')
        if target == SOURCE.resolve() or target.is_relative_to(SOURCE.resolve()):
            raise ValueError('A clone cannot be inside the original content volume.')
        if not uuid or uuid in {mounts[name].get('uuid') for name in ('/', str(SOURCE)) if name in mounts}:
            raise ValueError('A distinct filesystem UUID is required.')
        if result['filesystem'] not in FILESYSTEMS:
            raise ValueError('Use a mounted ext4, exFAT or NTFS filesystem.')
        if result['read_only']:
            raise ValueError('The destination is mounted read-only.')
        result['free_bytes'] = shutil.disk_usage(target).free
        result['block_size'] = max(512, os.statvfs(target).f_frsize)
        parent = devices[next(iter(backing_disks(row['source'], devices)))]
        result['model'] = result['model'] or parent.get('model') or ''
        result['serial'] = result['serial'] or parent.get('serial') or ''
        result['id'] = identity({'uuid': uuid, 'path': str(target)})[:24]
        marker = journal_path(target)
        if marker.is_symlink():
            raise ValueError('Unexpected clone metadata symlink.')
        if marker.exists():
            saved = read_json(marker / 'state.json')
            if saved.get('generator') != GENERATOR or saved.get('target_uuid') != uuid:
                raise ValueError('This drive has unrelated preparation metadata.')
            result['resume'] = saved.get('state') != 'ready'
            result['prepared'] = saved.get('state') == 'ready'
            if result['prepared']:
                raise ValueError('This clone is already complete; its files will not be overwritten.')
        else:
            if any(p.name not in SYSTEM_METADATA for p in target.iterdir()):
                raise ValueError('Choose an empty drive; existing files are never erased or adopted.')
            result['resume'] = False
        result['eligible'] = True
    except (OSError, ValueError, KeyError) as error:
        result['reasons'].append(str(error))
    return result


def targets():
    mounts, devices = storage()
    result = []
    for path, row in mounts.items():
        if not row.get('source', '').startswith('/dev/'):
            continue
        try:
            roots = backing_disks(row['source'], devices)
            if not any(devices[key].get('tran') == 'usb' for key in roots):
                continue
            result.append(inspect_target(path, mounts, devices))
        except (OSError, ValueError):
            continue
    return result


def policy():
    value = read_json(ROOT / 'config/clone-policy.json')
    if value.get('schema') != 1 or not 1 <= value.get('reserve_gib', 0) <= 100:
        raise ValueError('Invalid clone capacity policy')
    return value


def public_manifest():
    from app.services.manifest import load_manifest
    from app.services.configuration_project import public
    return public(load_manifest(ROOT / 'dataark.yaml'))


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '\\' in value or any(p in ('', '.', '..') for p in path.parts):
        raise ValueError('Unsafe public content path')
    if not path.parts or str(path) != value:
        raise ValueError('Use a normalized relative content path')
    return path


def public_name(relative):
    path = safe_relative(relative)
    return not any(part.startswith('.') or part.startswith('$') or part in SECRET_NAMES
                   or part.startswith('ssh_host_') for part in path.parts) and path.suffix.lower() not in {'.key', '.pem', '.p12', '.pfx'}


def inventory(manifest, settings, source=SOURCE):
    source = Path(source)
    units = []
    covered = set()
    roots = [(item['path'], item['title'], item['priority']) for item in settings['public_directories']]
    repositories = {item['id']: item for item in manifest['repositories']}
    roots += [(item['relative_path'], item.get('title', item['id']), 1)
              for item in manifest['assets']
              if item['relative_path'].endswith('.zim') and not item.get('removed')
              and repositories[item['repository_id']].get('enabled', True)]
    for name, title, priority in roots:
        safe_relative(name)
        if any(name == unit['id'] or name.startswith(unit['id']+'/') or unit['id'].startswith(name+'/') for unit in units):
            raise ValueError('Overlapping clone collection paths')
        path = source / name
        if path.is_symlink() or not path.exists():
            continue
        files = []
        def walk(directory):
            for child in sorted(directory.iterdir()):
                relative = child.relative_to(source).as_posix()
                if child.is_symlink() or not public_name(relative):
                    continue
                if child.is_dir():
                    walk(child)
                elif stat.S_ISREG(child.stat().st_mode):
                    info = child.stat()
                    files.append({'path': relative, 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
        if path.is_dir():
            walk(path)
        elif public_name(name) and stat.S_ISREG(path.stat().st_mode):
            info = path.stat()
            files.append({'path': name, 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
        if files:
            covered.update(item['path'] for item in files)
            units.append({'id': name, 'title': title, 'priority': priority, 'files': files,
                          'bytes': sum(item['bytes'] for item in files)})
    # Explicit public files outside configured collection directories remain eligible.
    for item in manifest['assets']:
        name = item['relative_path']
        if name in covered or item.get('removed') or not repositories[item['repository_id']].get('enabled', True):
            continue
        if not public_name(name) or (source / name).is_symlink() or not (source / name).is_file():
            continue
        path = source / name
        if not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('Public content path escapes its volume')
        info = path.stat()
        units.append({'id': name, 'title': item.get('title', item['id']), 'priority': 1,
                      'files': [{'path': name, 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns}],
                      'bytes': info.st_size})
    return units


def choose(units, mode, free, kit_bytes, reserve, block_size=4096):
    budget = free - kit_bytes - reserve
    selected, skipped = [], []
    for original in sorted(units, key=lambda unit: (unit['priority'], unit['bytes'], unit['id'])):
        unit = copy.deepcopy(original)
        unit['allocated_bytes'] = sum(((item['bytes'] + block_size - 1) // block_size) * block_size for item in unit['files'])
        if mode == 'config':
            reason = 'Content was not requested'
        elif mode == 'fit' and unit['allocated_bytes'] > budget:
            reason = 'Complete collection does not fit within the remaining budget'
        else:
            selected.append(unit)
            budget -= unit['allocated_bytes']
            continue
        skipped.append({'id': unit['id'], 'title': unit['title'], 'bytes': unit['bytes'], 'reason': reason})
    return selected, skipped, budget >= 0


def source_revision():
    return subprocess.check_output(['git', '-c', 'safe.directory='+str(ROOT), '-C', str(ROOT),
                                    'rev-parse', 'HEAD'], text=True, timeout=10).strip()


def kit_allowance(manifest):
    # The reserve is additional to this conservative allowance for software/config.
    rows = subprocess.check_output(['git', '-c', 'safe.directory='+str(ROOT), '-C', str(ROOT),
                                    'ls-tree', '-r', '-l', 'HEAD'], text=True, timeout=15)
    sizes = [int(row.split('\t', 1)[0].split()[-1]) for row in rows.splitlines()
             if row.split('\t', 1)[0].split()[-1].isdigit()]
    return max(256 * 1024**2, sum(sizes) + len(json.dumps(manifest).encode()) * 8 + 128 * 1024**2)


def build_plan(target, mode='config'):
    if mode not in {'config', 'fit', 'populated'}:
        raise ValueError('Unknown clone mode')
    device = inspect_target(target)
    if not device['eligible']:
        raise ValueError('; '.join(device['reasons']))
    if device.get('resume'):
        plan = read_json(journal_path(target) / 'plan.json')
        if plan['target']['path'] != str(Path(target).resolve()):
            raise ValueError('Resume at the original mount path')
        if plan['mode'] != mode:
            raise ValueError('Resume using the original clone mode')
        if plan_identity(plan) != plan.get('plan_id'):
            raise ValueError('Saved clone plan changed; preserve it for inspection')
        return plan
    manifest, settings = public_manifest(), policy()
    units = inventory(manifest, settings, SOURCE)
    allowance = kit_allowance(manifest)
    reserve = int(settings['reserve_gib'] * 1024**3)
    selected, skipped, fits = choose(units, mode, device['free_bytes'], allowance, reserve, device['block_size'])
    plan = {'schema': 1, 'generator': GENERATOR, 'mode': mode, 'target': device,
            'source_uuid': storage()[0][str(SOURCE)].get('uuid'), 'source_revision': source_revision(),
            'manifest_sha256': identity(manifest), 'kit_bytes': allowance, 'reserve_bytes': reserve,
            'selected': selected, 'skipped': skipped, 'fits': fits,
            'content_bytes': sum(unit['bytes'] for unit in selected),
            'allocated_bytes': sum(unit['allocated_bytes'] for unit in selected)}
    if not plan['source_uuid']:
        raise ValueError('Original content filesystem UUID is required')
    plan['plan_id'] = plan_identity(plan)
    return plan


def plan_identity(plan):
    basis = copy.deepcopy(plan)
    basis['target'].pop('free_bytes', None)
    basis.pop('fits', None)
    basis.pop('plan_id', None)
    return identity(basis)


def summary(plan):
    result = {key: value for key, value in plan.items() if key != 'selected'}
    result['selected'] = [{key: value for key, value in unit.items() if key != 'files'} |
                          {'file_count': len(unit['files'])} for unit in plan['selected']]
    args = ['sudo', '/opt/dataark/venv/bin/python', '/opt/dataark/tools/replicate_drive.py',
            '--target', plan['target']['path'], '--mode', plan['mode'], '--accept-plan', plan['plan_id'], '--apply']
    if journal_path(plan['target']['path']).exists():
        args.append('--resume')
    result['command'] = shlex.join(args)
    return result


def checked_path(root, relative):
    safe_relative(relative)
    path = Path(root)
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Unexpected source or destination symlink')
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Path escapes volume')
    return path


def copy_file(source, target, item, marker, reserve, progress=lambda amount: None, guard=lambda: None):
    guard()
    original = checked_path(source, item['path'])
    info = original.stat()
    if not stat.S_ISREG(info.st_mode) or (info.st_size, info.st_mtime_ns) != (item['bytes'], item['mtime_ns']):
        raise ValueError('Source file changed after planning: '+item['path'])
    destination = checked_path(target, item['path'])
    key = hashlib.sha256(item['path'].encode()).hexdigest()
    receipt = marker / 'verified' / (key+'.json')
    if destination.exists():
        if not receipt.is_file():
            raise ValueError('Refusing to overwrite an unowned destination file: '+item['path'])
        saved = read_json(receipt)
        if saved['bytes'] != item['bytes'] or digest(destination) != saved['sha256'] or digest(original) != saved['sha256']:
            raise ValueError('A completed clone file changed; preserve and inspect it before resuming')
        return saved
    partial = checked_path(marker, 'partial/'+key+'.part')
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.parent.chmod(0o700)
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > item['bytes']:
        raise ValueError('Partial clone file exceeds its source size')
    checksum = hashlib.sha256()
    with original.open('rb') as src:
        if offset:
            with partial.open('rb') as previous:
                remaining = offset
                while remaining:
                    expected = src.read(min(2*1024**2, remaining))
                    if previous.read(len(expected)) != expected or not expected:
                        raise ValueError('Partial clone differs from its source; no bytes were overwritten')
                    checksum.update(expected)
                    remaining -= len(expected)
        if shutil.disk_usage(target).free < item['bytes']-offset+reserve:
            raise ValueError('Available space changed; resume after reviewing destination capacity')
        with partial.open('ab') as dst:
            for block in iter(lambda: src.read(2*1024**2), b''):
                guard()
                if shutil.disk_usage(target).free < len(block)+reserve:
                    raise ValueError('Destination reserve reached; partial file retained')
                dst.write(block)
                checksum.update(block)
                progress(dst.tell())
            dst.flush()
            os.fsync(dst.fileno())
    if original.stat().st_size != item['bytes'] or original.stat().st_mtime_ns != item['mtime_ns']:
        raise ValueError('Source changed while copying; partial file retained')
    value = checksum.hexdigest()
    if partial.stat().st_size != item['bytes'] or digest(partial) != value:
        raise ValueError('Destination checksum verification failed')
    guard()
    destination.parent.mkdir(parents=True, exist_ok=True)
    checked_path(target, item['path'])
    partial.chmod(0o644)
    # Write the verified receipt before rename, allowing a crash on either side.
    saved = {'path': item['path'], 'bytes': item['bytes'], 'sha256': value}
    save(receipt, saved)
    partial.replace(destination)
    descriptor = os.open(destination.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return saved


def publish_catalogue(target, plan, receipts):
    report = {'generator': GENERATOR, 'plan_id': plan['plan_id'], 'mode': plan['mode'],
              'source_revision': plan['source_revision'], 'files': receipts,
              'included': [unit['title'] for unit in plan['selected']], 'skipped': plan['skipped']}
    save(target / 'CLONE-REPORT.json', report)
    links = ''.join('<li><a href="'+html.escape(item['path'], quote=True)+'">'+
                    html.escape(item['path'])+'</a></li>' for item in receipts)
    skipped = ''.join('<li>'+html.escape(unit['title'])+' — '+html.escape(unit['reason'])+'</li>'
                      for unit in plan['skipped'])
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Data Ark drive clone</title><style>body{font:17px/1.6 system-ui;background:#f7f2e6;color:#203e54;max-width:70rem;margin:2rem auto;padding:1rem}a{color:#075a96}li{margin:.4rem 0}</style><h1>Data Ark drive clone</h1><p><a href="START-ARK.html">Set up a Pi from this drive</a> · <a href="DATA-ARK-CONFIG/index.html">Public configuration</a> · <a href="CLONE-REPORT.json">Verified copy report</a></p><p>'+str(len(receipts))+' verified public files. No credentials or household backups were copied.</p><h2>Copied content</h2><ul>'+links+'</ul><details><summary>Content not included</summary><ul>'+skipped+'</ul></details></html>'
    for name in ('START-HERE.html', 'BROWSE.html'):
        (target/name).write_text(page, encoding='utf-8')
    (target/'README-DATA-ARK.txt').write_text('Data Ark clone\nOpen START-HERE.html to browse verified copied files, or START-ARK.html for setup.\nSee CLONE-REPORT.json for copied and skipped content.\n', encoding='utf-8')


def durable_kit(target, guard):
    files = {}
    for name in ('DATA-ARK-CONFIG', 'DATA-ARK-RECOVERY', 'START-ARK.sh', 'START-ARK.html', 'START-ARK.txt'):
        root = target/name
        for path in ([root] if root.is_file() else root.rglob('*')):
            guard()
            if path.is_symlink():
                raise ValueError('Unexpected installer-kit symlink')
            if path.is_file():
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
                if path.name != 'kit.json':
                    files[path.relative_to(target).as_posix()] = digest(path)
    return files


def apply(plan, accepted, resume=False):
    if os.geteuid() != 0:
        raise ValueError('Copying requires local caretaker access through sudo')
    if accepted != plan['plan_id'] or plan_identity(plan) != accepted or not plan['fits']:
        raise ValueError('Accept the exact fitting preview plan before copying')
    with ExitStack() as stack:
        return apply_locked(plan, accepted, resume, stack)


def apply_locked(plan, accepted, resume, stack):
    import fcntl
    for path in [STATUS/'worker.lock', Path('/var/lib/dataark/updates/worker.lock'), Path('/var/lib/dataark/maps/worker.lock')]:
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = stack.enter_context(path.open('a'))
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    target = Path(plan['target']['path']).resolve()
    device = inspect_target(target)
    if not device['eligible'] or device['uuid'] != plan['target']['uuid']:
        raise ValueError('Destination identity or eligibility changed')
    volume_device = target.stat().st_dev
    source_device = SOURCE.stat().st_dev
    def guard():
        if not target.is_mount() or target.stat().st_dev != volume_device:
            raise ValueError('Destination disconnected; no further writes are permitted')
        if not SOURCE.is_mount() or SOURCE.stat().st_dev != source_device:
            raise ValueError('Original content drive disconnected')
    guard()
    if identity(public_manifest()) != plan['manifest_sha256']:
        raise ValueError('Public configuration changed; review a new plan')
    if storage()[0][str(SOURCE)].get('uuid') != plan['source_uuid']:
        raise ValueError('Original content volume changed')
    marker = target/MARKER
    existing = journal_path(target)
    if existing.exists() != resume:
        raise ValueError('Use --resume only for this tool’s matching incomplete clone')
    if not resume and build_plan(target, plan['mode'])['plan_id'] != accepted:
        raise ValueError('Source content changed after the preview')
    state = {'schema': 1, 'generator': GENERATOR, 'state': 'preparing', 'target_uuid': device['uuid'],
             'target': str(target), 'plan_id': accepted, 'mode': plan['mode'], 'files_complete': 0,
             'files_total': sum(len(unit['files']) for unit in plan['selected']),
             'bytes_total': plan['content_bytes'], 'pid': os.getpid(), 'updated_at': time.time()}
    if resume:
        if existing != marker:
            existing.replace(marker)
        state = read_json(marker/'state.json') | {'pid': os.getpid()}
        if read_json(marker/'plan.json')['plan_id'] != accepted:
            raise ValueError('Clone marker does not match the approved plan')
    else:
        # Rename a fully initialized journal into place, rather than exposing an
        # unresumable marker if power fails between creating its two files.
        pending = target/'.dataark-clone-initializing'
        pending.mkdir(mode=0o755, exist_ok=True)
        save(pending/'state.json', state)
        save(pending/'plan.json', plan)
        pending.replace(marker)
    os.chown(target, 1000, 1000)
    def update(**changes):
        state.update(changes, updated_at=time.time())
        guard()
        save(marker/'state.json', state)
        save(STATUS/'status.json', state)
    try:
        update(state='preparing')
        if not (marker/'kit-ready.json').exists():
            from tools.content_profile import export
            profile = marker/'profile'
            export(profile)
            if identity(public_manifest()) != plan['manifest_sha256']:
                raise ValueError('Configuration changed while preparing the clone kit')
            from tools.replicate_drive import kit_files
            metadata = kit_files(target, profile=profile/'content.yaml', revision=plan['source_revision'])
            guard()
            save(marker/'kit-ready.json', {'metadata': metadata, 'files': durable_kit(target, guard)})
        else:
            for relative, expected in read_json(marker/'kit-ready.json')['files'].items():
                guard()
                if digest(checked_path(target, relative)) != expected:
                    raise ValueError('Installer kit changed; preserve and inspect it before resuming')
        update(state='copying', files_complete=0)
        receipts = []
        last = [0.0]
        for unit in plan['selected']:
            for item in unit['files']:
                def progress(amount):
                    if time.monotonic()-last[0] >= 2:
                        update(current=item['path'], current_bytes=amount)
                        last[0] = time.monotonic()
                receipts.append(copy_file(SOURCE, target, item, marker, plan['reserve_bytes'], progress, guard))
                update(files_complete=len(receipts), current=item['path'], current_bytes=item['bytes'])
        guard()
        publish_catalogue(target, plan, receipts)
        metadata = read_json(target/'DATA-ARK-RECOVERY/kit.json')
        metadata.update(preparation_state='ready', preparation_mode=plan['mode'], clone_plan_id=accepted,
                        copied_files=len(receipts), skipped_collections=len(plan['skipped']))
        save(target/'DATA-ARK-RECOVERY/kit.json', metadata)
        for name in ('START-HERE.html', 'BROWSE.html', 'README-DATA-ARK.txt'):
            guard()
            with (target/name).open('rb') as stream:
                os.fsync(stream.fileno())
        update(state='ready', current=None)
    except BaseException as error:
        state.update(state='interrupted', error=str(error) or type(error).__name__, updated_at=time.time())
        save(STATUS/'status.json', state)
        try:
            guard()
            save(marker/'state.json', state)
        except (OSError, ValueError):
            pass
        raise
    return state


def status():
    if not (STATUS/'status.json').is_file():
        return {'state': 'idle'}
    value = read_json(STATUS/'status.json')
    if value.get('state') in {'preparing', 'copying'} and not Path('/proc', str(value.get('pid'))).exists():
        value.update(state='interrupted', error='The worker stopped; resume the matching clone from the caretaker terminal.')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path)
    parser.add_argument('--mode', choices=['config', 'fit', 'populated'], default='config')
    parser.add_argument('--targets', action='store_true')
    parser.add_argument('--accept-plan')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.targets:
        print(json.dumps({'drives': targets()}, indent=2))
        return
    if args.target is None:
        parser.error('--target is required for a preview or copy')
    plan = build_plan(args.target, args.mode)
    if not args.apply:
        print(json.dumps(summary(plan), indent=2))
        return
    result = apply(plan, args.accept_plan, args.resume)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
