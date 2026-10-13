#!/usr/bin/env python3
"""Read an SMB source into /dev/null and retain private error diagnostics."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import bugout as b


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task_id')
    args = parser.parse_args()
    cfg, _ = b.configuration()
    task = next((t for t in cfg.get('tasks', []) if t['id'] == args.task_id), None)
    if not task or task.get('kind','smb') != 'smb':
        parser.error('Choose a configured SMB source')
    os.umask(0o077)
    with tempfile.NamedTemporaryFile(prefix='source-diagnostic-',suffix='.log',dir=b.STATE,delete=False) as log:
        filename = log.name
        try:
            with b.smb_command(task,remembered_only=True) as command:
                result = subprocess.run(command + ['-Tc','-'],stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=log,timeout=180)
            print('SMB archive-read exit:', result.returncode)
        except subprocess.TimeoutExpired:
            print('Diagnostic stopped after 180 seconds.')
        except (OSError,ValueError):
            print('Unable to run diagnostic; check installed SMB client and remembered credentials.')
            return 1
    with open(filename,'rb') as log:
        errors = log.read(1024*1024).decode(errors='replace')
    print('SMB statuses:', ', '.join(sorted(set(re.findall(r'\bNT_STATUS_[A-Z0-9_]+\b', errors)))) or 'none')
    print('Private diagnostic:',filename)
    print('Contains source filenames; do not publish. No archive was saved or source files changed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
