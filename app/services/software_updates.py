"""Read-only software release discovery; never downloads or executes a package."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
RELEASES='https://api.github.com/repos/DavJenkins/pharos/releases?per_page=100'
LOCK=threading.Lock()
CACHE={}
SHA=re.compile(r'[0-9a-f]{40}')
TAG=re.compile(r'bootstrap-([0-9]{4}\.[0-9]{2}\.[0-9]{2})(?:-preview\.([0-9]+))?')


def installed():
    try:
        value=json.loads((ROOT/'app/static/assets/build-info.json').read_text())
        return {key:value.get(key) for key in ('revision','branch','source_date','published_at')}
    except (OSError,ValueError,AttributeError):return {'revision':None}


def read_releases():
    request=Request(RELEASES,headers={'Accept':'application/vnd.github+json','User-Agent':'Pharos-Data-Ark-update-check/1'})
    with urlopen(request,timeout=10) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Release response exceeds the size limit')
    value=json.loads(raw)
    if not isinstance(value,list):raise ValueError('Unexpected release response')
    return value


def candidates(releases,preview=False):
    result=[]
    for item in releases:
        if not isinstance(item,dict):continue
        tag=item.get('tag_name','')
        match=TAG.fullmatch(tag) if isinstance(tag,str) else None
        if not match or item.get('draft') or (not preview and (item.get('prerelease') or match[2])):continue
        # A handbook or bootstrap archive is not an in-place software updater.
        asset='data-ark-bootstrap-'+tag.removeprefix('bootstrap-')+'.tar.gz'
        if not any(a.get('name')==asset and a.get('state')=='uploaded' for a in item.get('assets',[]) if isinstance(a,dict)):continue
        result.append((match[1],0 if match[2] else 1,int(match[2] or 0),item))
    return [row[3] for row in sorted(result,key=lambda row:row[:3],reverse=True)]


def relationship(current,target):
    if not isinstance(current,str) or not isinstance(target,str) or not SHA.fullmatch(current) or not SHA.fullmatch(target):return 'uncompared'
    if current==target:return 'same'
    def ancestor(first,second):
        return subprocess.run(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'merge-base','--is-ancestor',first,second],capture_output=True,timeout=3,check=False).returncode
    try:
        if ancestor(target,current)==0:return 'development_ahead'
        if ancestor(current,target)==0:return 'newer_release'
    except (OSError,subprocess.SubprocessError):pass
    return 'uncompared'


def check(preview=False):
    with LOCK:
        previous=CACHE.get(preview)
        if previous and time.monotonic()-previous[0]<60:return previous[1]
        current=installed()
        result={'installed':current,'channel':'preview' if preview else 'stable',
                'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'installation_supported':False,'release':None}
        try:
            choices=candidates(read_releases(),preview)
            if not choices:
                result.update(state='no_release',message='No published software release is available in this channel. Preview releases can be checked separately.')
            else:
                item=choices[0];tag=item['tag_name'];relation=relationship(current.get('revision'),item.get('target_commitish'))
                result['release']={'tag':tag,'published_at':item.get('published_at'),'preview':bool(item.get('prerelease') or '-preview.' in tag),
                    'url':'https://github.com/DavJenkins/pharos/releases/tag/'+tag,'source_revision':item.get('target_commitish')}
                messages={'same':'This build matches the published source revision.',
                    'development_ahead':'This development build already contains the published release and newer changes. Do not replace it with the older bootstrap kit.',
                    'newer_release':'A newer published source revision is available for review.',
                    'uncompared':'A published release is available, but its revision cannot be reliably compared with this build.'}
                result.update(state=relation,message=messages[relation]+' The published kit is for bootstrap/recovery; it is not an in-place update package.')
        except Exception:
            result.update(state='unavailable',message='The release service could not be checked. The Ark may be offline, or the service may be unavailable or rate limited. This does not mean the software is current.')
            if previous:result['previous_check']={key:previous[1].get(key) for key in ('checked_at','state','release')}
        CACHE[preview]=(time.monotonic(),result)
        return result
