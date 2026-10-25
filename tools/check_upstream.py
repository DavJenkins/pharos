#!/usr/bin/env python3
"""Explicitly check configured asset download sources; never download payloads."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import load_manifest, atomic_write, ManifestError
from app.services.upstream import check_assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', nargs='?', type=Path, default=ROOT / 'dataark.yaml')
    args = parser.parse_args()
    try:
        data = load_manifest(args.manifest)
        directory = args.manifest.resolve().parent / '.cache'
        directory.mkdir(exist_ok=True)
        with (directory/'source-check.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            state = check_assets(data.get('assets', []))
            atomic_write(directory/'manifest-upstream.json', json.dumps(state, indent=2).encode())
    except (ManifestError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    for key, record in state['assets'].items():
        print(f'{key}: {record["status"]} (checked {record["checked_at"]})')
    print(f'Checked {len(state["assets"])} assets. The dashboard reads these observations automatically; rebuild/deploy also refreshes its static fallback.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
