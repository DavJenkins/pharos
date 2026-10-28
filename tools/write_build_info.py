#!/usr/bin/env python3
"""Publish a source fingerprint and the UTC publication time, without secrets."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def git(*args):
    try:
        return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),*args],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
    except (OSError,subprocess.SubprocessError):return ''

def build_info():
    digest=hashlib.sha256()
    for directory in ('app','tools','deploy'):
        for path in sorted((ROOT/directory).rglob('*')):
            if not path.is_file() or any(part in ('vendor','__pycache__','.git') for part in path.parts):continue
            if path.suffix not in ('.py','.js','.css','.html','.sh'):continue
            digest.update(path.relative_to(ROOT).as_posix().encode()+b'\0'+path.read_bytes()+b'\0')
    return {'schema':1,'revision':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),
            'source_date':git('show','-s','--format=%cI','HEAD'),
            'source_fingerprint':digest.hexdigest(),'published_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}

if __name__=='__main__':
    target=ROOT/'app/static/assets/build-info.json'
    target.write_text(json.dumps(build_info(),indent=2)+'\n');target.chmod(0o644)
