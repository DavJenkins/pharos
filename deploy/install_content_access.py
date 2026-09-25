#!/usr/bin/env python3
"""Install read-only content access, preserving and validating server configuration."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

MARKER = '# Managed by Data Ark content access v1'
APACHE = MARKER + '''
Alias /library-files/ /mnt/storage/
<Directory "/mnt/storage">
    Options Indexes
    AllowOverride None
    Require all granted
    SetHandler default-handler
    DirectoryIndex disabled
    IndexIgnore .??* bugout-drop "System Volume Information" "$RECYCLE.BIN"
    AddType application/octet-stream .zim .exe .dll .pak .sh .py
    <FilesMatch "^\\.">
        Require all denied
    </FilesMatch>
</Directory>
<Directory "/mnt/storage/bugout-drop">
    Require all denied
</Directory>
<Directory "/mnt/storage/System Volume Information">
    Require all denied
</Directory>
<Directory "/mnt/storage/$RECYCLE.BIN">
    Require all denied
</Directory>
'''

def update_share(text, section, settings):
    headers = list(re.finditer(r'^[ \t]*\[([^]\r\n]+)\][^\r\n]*', text, re.M))
    matches = [(index, match) for index, match in enumerate(headers) if match.group(1).lower() == section.lower()]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one [{section}] section; no configuration changed.')
    index, match = matches[0]
    end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
    block = text[match.end():end]
    keys = set(settings)
    if 'read only' in keys:
        keys.update(('writeable', 'writable'))
    lines = []
    for line in block.splitlines():
        key = line.split('=', 1)[0].strip().lower() if '=' in line else ''
        if key not in keys:
            lines.append(line)
    body = '\n'.join(lines).rstrip()
    additions = '\n'.join(f'    {key} = {value}' for key, value in settings.items())
    return text[:match.end()] + body + '\n' + additions + '\n\n' + text[end:]

def candidate_samba(text):
    text = update_share(text, 'Offline-Archives', {
        'path':'/mnt/storage', 'read only':'yes', 'write list':'',
        'browseable':'yes', 'force user':'admin',
        'veto files':'/bugout-drop/System Volume Information/$RECYCLE.BIN/',
    })
    return update_share(text, 'Bugout-Staging', {'force user':'admin'})

def write_atomic(path, data, mode=0o644):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        stream.write(data)
        temp = Path(stream.name)
    try:
        temp.chmod(mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def check(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed: {result.stderr.strip()}')
    return result.stdout

def main():
    import pwd
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo python3 deploy/install_content_access.py')
    root = Path('/mnt/storage')
    if not root.is_mount():
        raise SystemExit('Expected SSD mount is missing; no configuration changed.')
    if (root / 'bugout-drop').is_symlink():
        raise SystemExit('Unexpected staging symlink; inspect manually.')
    if pwd.getpwnam('admin').pw_uid != root.stat().st_uid:
        raise SystemExit('SSD ownership does not match admin; inspect mount options before proceeding.')
    modules = check(['apache2ctl', '-M'])
    for module in ('alias_module', 'autoindex_module', 'dir_module', 'mime_module'):
        if module not in modules:
            raise SystemExit(f'{module} must be enabled before this installer runs.')
    smb = Path('/etc/samba/smb.conf')
    apache = Path('/etc/apache2/conf-available/dataark-content.conf')
    enabled = Path('/etc/apache2/conf-enabled/dataark-content.conf')
    if smb.is_symlink() or apache.is_symlink():
        raise SystemExit('Unexpected configuration symlink; inspect manually.')
    if enabled.exists() or enabled.is_symlink():
        if not enabled.is_symlink() or enabled.resolve() != apache:
            raise SystemExit('Unexpected enabled Apache configuration path.')
    old_smb = smb.read_bytes()
    smb_mode = smb.stat().st_mode & 0o777
    old_apache = apache.read_bytes() if apache.exists() else None
    old_enabled = enabled.is_symlink()
    if old_apache is not None and MARKER.encode() not in old_apache:
        raise SystemExit('Refusing to overwrite an Apache configuration owned by another tool.')
    new_smb = candidate_samba(old_smb.decode('utf-8')).encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=smb.parent) as test:
        test.write(new_smb)
        test.flush()
        check(['testparm', '-s', test.name])
    backup_parent = Path('/var/backups/dataark-content')
    backup_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=backup_parent))
    (backup / 'smb.conf').write_bytes(old_smb)
    if old_apache is not None:
        (backup / 'dataark-content.conf').write_bytes(old_apache)
    # Generate orientation files only after preflight; refuse to overwrite unrelated files.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.publish_content import publish
    (root / 'bugout-drop').mkdir(exist_ok=True)
    count = publish(root)
    try:
        write_atomic(smb, new_smb, smb_mode)
        write_atomic(apache, APACHE.encode('utf-8'))
        if not old_enabled:
            enabled.symlink_to(apache)
        check(['apache2ctl', 'configtest'])
        check(['systemctl', 'reload', 'apache2'])
        check(['systemctl', 'reload', 'smbd'])
    except Exception:
        write_atomic(smb, old_smb, smb_mode)
        if old_apache is None:
            apache.unlink(missing_ok=True)
        else:
            write_atomic(apache, old_apache)
        if not old_enabled:
            enabled.unlink(missing_ok=True)
        for service in ('apache2', 'smbd'):
            subprocess.run(['systemctl', 'reload', service], capture_output=True, timeout=30, check=False)
        raise
    print(f'Published portable orientation files for {count} library files.')
    print(f'Configuration backup: {backup}')
    print('HTTP: http://dataark/library-files/START-HERE.html')
    print(r'SMB: \\dataark\Offline-Archives (read-only; staging remains separate)')
    print('Direct SSD: open START-HERE.html on OfflineRepo.')
    print('Existing archive files were not moved, reformatted, or rewritten.')

if __name__ == '__main__':
    main()
