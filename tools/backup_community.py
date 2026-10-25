#!/usr/bin/env python3
"""Private daily online snapshot of the local board; never placed on public shares."""
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.community import snapshot, settings

def main():
    folder=Path('/var/backups/dataark-community')
    if not folder.is_dir():raise SystemExit('Run the community board installer first.')
    name='board-'+datetime.now(timezone.utc).strftime('%Y-%m-%d')+'.sqlite3'
    result=snapshot(folder/name)
    keep=max(1,min(30,int(settings()['backup_copies'])))
    for old in sorted(folder.glob('board-????-??-??.sqlite3'),reverse=True)[keep:]:
        if old.is_file() and not old.is_symlink():old.unlink()
    print('Board backup saved:',result)

if __name__=='__main__':main()
