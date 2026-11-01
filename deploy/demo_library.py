"""Optional capped system-card library. Only an exclusively created regular file is formatted."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

GIB = 1024 ** 3
DEFAULT_GIB = 4
OS_RESERVE_GIB = 10
IMAGE = Path('/var/lib/dataark/demo-library.ext4')
STATE = Path('/var/lib/dataark/demo-library.json')
MOUNT = Path('/mnt/storage')


def plan(size_gib, free_bytes, existing=False):
    if type(size_gib) is not int or not 2 <= size_gib <= 1024:
        raise ValueError('Choose a whole number from 2 to 1024 GiB.')
    remaining = free_bytes if existing else free_bytes - size_gib * GIB
    if remaining < OS_RESERVE_GIB * GIB:
        raise ValueError('Demo allocation must leave at least 10 GiB free for the operating system.')
    return {'mode': 'demo', 'label': 'Demo library on the system card',
            'size_gib': size_gib, 'capacity_bytes': size_gib * GIB,
            'system_free_after_bytes': remaining, 'system_reserve_gib': OS_RESERVE_GIB}


def _save(path, value):
    temp = path.with_suffix('.new')
    with temp.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.chmod(0o600)
    temp.replace(path)


def create(size_gib, image=IMAGE, state=STATE, mount=MOUNT, fstab=Path('/etc/fstab'), runner=subprocess.run):
    for path in (image, state, mount, fstab):
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError('Demo storage paths must not contain symlinks.')
    image.parent.mkdir(parents=True, exist_ok=True)
    saved = json.loads(state.read_text()) if state.is_file() else None
    if image.exists():
        info = image.stat()
        if not saved or not stat.S_ISREG(info.st_mode) or saved.get('image') != str(image) or saved.get('inode') != info.st_ino or saved.get('device') != info.st_dev or saved.get('capacity_bytes') != size_gib * GIB or info.st_size != size_gib * GIB:
            raise ValueError('Existing demo image is unowned or changed; nothing was formatted.')
        if saved.get('stage') != 'ready':
            raise ValueError('Interrupted demo creation requires inspection; existing image was not reformatted.')
    elif saved:
        raise ValueError('Recorded demo image is missing; it will not be silently recreated.')
    spec = plan(size_gib, shutil.disk_usage(image.parent).free, existing=bool(saved))
    mounted = runner(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', str(mount)], capture_output=True, text=True)
    if mounted.returncode == 0:
        if not saved:
            raise ValueError('A content volume is mounted; the demo cannot replace it.')
        loop = runner(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', str(mount)], capture_output=True, text=True, check=True).stdout.strip()
        backing = runner(['losetup', '-n', '-O', 'BACK-FILE', loop], capture_output=True, text=True, check=True).stdout.strip()
        if Path(backing).resolve() != image.resolve():
            raise ValueError('A different content volume occupies the demo mount.')
        return spec
    if mount.exists() and any(mount.iterdir()):
        raise ValueError('Content mount directory is not empty; nothing was hidden or replaced.')
    text = fstab.read_text()
    entry = f'{image} {mount} ext4 loop,nofail,nodev,nosuid,x-systemd.device-timeout=10 0 0'
    for line in text.splitlines():
        fields = line.split()
        if len(fields) > 1 and not line.lstrip().startswith('#') and fields[1] == str(mount) and line != entry:
            raise ValueError('An existing content-drive mount is configured; the demo cannot replace it.')
    if not saved:
        fd = os.open(image, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            os.posix_fallocate(fd, 0, spec['capacity_bytes'])
            os.fsync(fd)
        finally:
            os.close(fd)
        info = image.stat()
        saved = dict(spec, image=str(image), inode=info.st_ino, device=info.st_dev, stage='allocated')
        _save(state, saved)
        runner(['mkfs.ext4', '-q', '-F', '-L', 'DataArkDemo', str(image)], check=True)
        saved['stage'] = 'ready'
        _save(state, saved)
    mount.mkdir(parents=True, exist_ok=True)
    runner(['mount', '-t', 'ext4', '-o', 'loop,nodev,nosuid', str(image), str(mount)], check=True)
    os.chown(mount, 1000, 1000)
    mount.chmod(0o755)
    marker = mount / 'DEMO-LIBRARY.json'
    marker.write_text(json.dumps({'label': spec['label'], 'size_gib': size_gib, 'capacity_bytes': spec['capacity_bytes']}, indent=2) + '\n')
    marker.chmod(0o644)
    if entry not in text.splitlines():
        backup = state.parent / 'fstab.before-demo'
        if not backup.exists():
            shutil.copy2(fstab, backup)
        fstab.write_text(text.rstrip() + '\n# Optional capped Data Ark demo library\n' + entry + '\n')
    runner(['systemctl', 'daemon-reload'], check=True)
    return spec


def samples(repo, root=MOUNT):
    """Explicitly approved, fixed-size/checksummed samples; retain the full source catalogue."""
    import urllib.request
    config = json.loads((repo / 'config/demo-library.json').read_text())
    if not root.is_mount() or not (root / 'DEMO-LIBRARY.json').is_file():
        raise ValueError('The marked demo volume must be mounted before adding samples.')
    for item in config['samples']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe sample destination')
        target = root / relative
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError('Sample destination contains a symlink')
        target.parent.mkdir(parents=True, exist_ok=True)
        if 'source' in item:
            source = repo / item['source']
            if not source.resolve().is_relative_to(repo.resolve()):
                raise ValueError('Sample source is outside the repository')
            if target.exists():
                if hashlib.file_digest(target.open('rb'), 'sha256').digest() != hashlib.file_digest(source.open('rb'), 'sha256').digest():
                    raise ValueError('An existing sample differs; it was not overwritten.')
                continue
            with source.open('rb') as incoming:
                data = incoming.read(item['max_bytes'] + 1)
            if len(data) > item['max_bytes']:
                raise ValueError('Bundled sample exceeds its declared size limit')
            with target.open('xb') as outgoing:
                outgoing.write(data)
        else:
            if target.exists():
                if hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() != item['sha256']:
                    raise ValueError('An existing sample failed verification; it was not overwritten.')
                continue
            if shutil.disk_usage(root).free - item['bytes'] < GIB:
                raise ValueError('Sample must leave 1 GiB free inside the demo volume.')
            temp = target.with_suffix(target.suffix + '.download')
            if temp.exists():
                if temp.is_symlink() or not temp.is_file():raise ValueError('Unsafe partial sample')
                temp.unlink()
            h = hashlib.sha256(); count = 0
            try:
                with urllib.request.urlopen(item['url'], timeout=60) as incoming, temp.open('xb') as outgoing:
                    if not incoming.url.startswith('https://'):
                        raise ValueError('Sample redirected away from HTTPS')
                    while True:
                        block = incoming.read(1024 * 1024)
                        if not block:
                            break
                        count += len(block)
                        if count > item['bytes']:
                            raise ValueError('Sample exceeds its approved size')
                        outgoing.write(block); h.update(block)
                    outgoing.flush(); os.fsync(outgoing.fileno())
                if count != item['bytes'] or h.hexdigest() != item['sha256']:
                    raise ValueError('Sample size/checksum mismatch')
                temp.replace(target)
            except BaseException:
                if temp.exists(): temp.unlink()
                raise
        target.chmod(0o644)
    return config


def grow(size_gib, image=IMAGE, state=STATE, mount=MOUNT, runner=subprocess.run):
    """Grow only our mounted ext4 image; never shrink or format existing content."""
    for path in (image, state, mount):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Storage paths must not contain symlinks.')
    saved = json.loads(state.read_text())
    info = image.stat()
    old = saved['capacity_bytes']
    target = size_gib * GIB
    if saved.get('stage') != 'ready' or saved.get('image') != str(image) or not stat.S_ISREG(info.st_mode) or saved.get('inode') != info.st_ino or saved.get('device') != info.st_dev or info.st_size != old:
        raise ValueError('Image ownership or size changed; inspect before resizing.')
    if target < old:
        raise ValueError('Shrinking is not supported.')
    plan(size_gib, shutil.disk_usage(image.parent).free - (target-old), existing=True)
    loop = runner(['findmnt','-n','-o','SOURCE','--mountpoint',str(mount)],capture_output=True,text=True,check=True).stdout.strip()
    backing = runner(['losetup','-n','-O','BACK-FILE',loop],capture_output=True,text=True,check=True).stdout.strip()
    filesystem = runner(['findmnt','-n','-o','FSTYPE','--mountpoint',str(mount)],capture_output=True,text=True,check=True).stdout.strip()
    if not loop.startswith('/dev/loop') or Path(backing).resolve() != image.resolve() or filesystem != 'ext4':
        raise ValueError('Mounted volume is not the owned ext4 image.')
    if target == old:return saved
    journal = state.with_suffix('.resize.json')
    if journal.exists():raise ValueError('A previous resize needs inspection.')
    _save(journal, {'stage':'growing','old_bytes':old,'new_bytes':target,'image':str(image)})
    with image.open('r+b') as stream:
        os.posix_fallocate(stream.fileno(), old, target-old)
        os.fsync(stream.fileno())
    runner(['losetup','--set-capacity',loop],check=True)
    runner(['resize2fs',loop],check=True)
    saved.update(capacity_bytes=target,size_gib=size_gib,system_free_after_bytes=shutil.disk_usage(image.parent).free)
    _save(state,saved)
    marker=mount/'DEMO-LIBRARY.json'
    marker.write_text(json.dumps({'label':saved['label'],'size_gib':size_gib,'capacity_bytes':target},indent=2)+'\n')
    journal.unlink()
    return saved


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Grow the system-card library without replacing content.')
    parser.add_argument('--grow-gib',type=int,required=True)
    args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('Run with sudo.')
    print(json.dumps(grow(args.grow_gib),indent=2))
