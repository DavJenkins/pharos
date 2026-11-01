#!/usr/bin/python3
"""Report cached OS update availability and completed apt transactions; install nothing."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
STATE=Path('/var/lib/dataark/collection-changes/os-updates.json')


def pending_packages(text):
    return sorted(line.split()[0]+' '+line.split()[1] for line in text.splitlines()
                  if re.match(r'^[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?/\S+\s+\S+\s+',line))


def completed_transactions(text):
    result=[]
    for block in re.split(r'(?=^Start-Date:)',text,flags=re.M):
        start=re.search(r'^Start-Date:\s*(.+)$',block,re.M);end=re.search(r'^End-Date:\s*(.+)$',block,re.M)
        changes=re.findall(r'^(Install|Upgrade|Remove):\s*(.+)$',block,re.M)
        if not start or not end or not changes:continue
        counts={kind:len(re.findall(r'(?:^|\),\s*)([a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?)\s+\(',line)) for kind,line in changes}
        identity=hashlib.sha256(json.dumps([start[1],end[1],changes]).encode()).hexdigest()
        result.append({'id':identity,'title':'OS packages updated: '+', '.join(str(counts.get(k,0))+' '+label for k,label in [('Upgrade','upgraded'),('Install','installed'),('Remove','removed')])})
    return result


def report(pending, transactions, state=STATE):
    from app.services.collection_changes import safe_record
    previous=json.loads(state.read_text()) if state.exists() else None
    # First observation establishes a history baseline rather than replaying old upgrades.
    seen=set(previous.get('seen',[])) if previous else {t['id'] for t in transactions}
    for item in transactions:
        if item['id'] not in seen:
            safe_record('installed',collection_id='operating-system',action='os_update',title=item['title'],operation_id=item['id'])
        seen.add(item['id'])
    marker=hashlib.sha256(json.dumps(pending).encode()).hexdigest()
    safe_record('suggested' if pending else 'idle',collection_id='operating-system',action='os_update',
                title=str(len(pending))+' OS package updates available' if pending else '',
                operation_id=marker,activity_key='os_updates')
    state.parent.mkdir(parents=True,exist_ok=True)
    temp=state.with_suffix('.new');temp.write_text(json.dumps({'seen':[t['id'] for t in transactions][-200:],'pending_count':len(pending)},indent=2)+'\n');temp.replace(state)


def main():
    output=subprocess.run(['apt','list','--upgradable'],capture_output=True,text=True,timeout=60,check=True,env={**os.environ,'LC_ALL':'C'}).stdout
    history=Path('/var/log/apt/history.log')
    if history.exists():
        with history.open('rb') as stream:
            stream.seek(max(0,history.stat().st_size-1024*1024));text=stream.read().decode(errors='replace')
    else:text=''
    report(pending_packages(output),completed_transactions(text))


if __name__=='__main__':main()
