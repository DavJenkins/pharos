#!/usr/bin/python3 -I
"""Fixed, read-only support snapshot. No credentials or arbitrary input paths."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import stat

def redact(text):
    text=re.sub(r'(?i)(authorization["\s]*[:=]\s*)([^\r\n]+)',r'\1[redacted]',text)
    text=re.sub(r'''(?i)((?:password|passwd|passphrase|psk|token|secret|deletion_code|private_key|api_key)["\s]*[:=]\s*)("[^"\r\n]*"|'[^'\r\n]*'|[^,;}\r\n]+)''',r'\1[redacted]',text)
    text=re.sub(r'(?i)(https?://)[^\s/@:]+:[^\s/@]+@',r'\1[redacted]@',text)
    return text

def sanitize(value):
    if isinstance(value,dict):
        return {key:('[redacted]' if re.search(r'authorization|cookie|password|passwd|passphrase|psk|token|secret|private_key|api_key|deletion_code',key,re.I) else sanitize(item)) for key,item in value.items()}
    if isinstance(value,list):return [sanitize(item) for item in value]
    return redact(value) if isinstance(value,str) else value

def command(args,limit=12000):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=3,check=False,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'})
        text=result.stdout+result.stderr
        return redact(text[:limit]+('\n[truncated]' if len(text)>limit else ''))
    except (OSError,subprocess.SubprocessError) as error:return type(error).__name__+': telemetry unavailable'

def tail(path,limit=24000):
    try:
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(descriptor,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):return 'Not a regular log file'
            stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-limit))
            data=stream.read(limit).decode('utf-8',errors='replace')
        if size>limit:data='[older records omitted]\n'+data.split('\n',1)[-1]
        return redact(data)
    except OSError:return 'Not available'

def api(path):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8000/'+path,timeout=3) as response:
            raw=response.read(3*1024*1024+1)
            if len(raw)>3*1024*1024:return {'error':'Snapshot exceeded size limit'}
            return json.loads(raw)
    except Exception:return {'error':'API telemetry unavailable'}

def collect():
    report={'collected_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'scope':'Read-only troubleshooting snapshot. Passwords, private keys, tokens, household files and message bodies are excluded.',
            'build':tail('/var/www/html/assets/build-info.json',4096),
            'status':api('status'), 'debug_enabled':Path('/var/lib/ark/debug_status').exists(),
            'wifi_roles':tail('/run/dataark-wifi-roles.json',4096),'bugout':api('bugout/state'),'https':api('https/status')}
    report['hardware_model']=tail('/proc/device-tree/model',1024).rstrip('\0')
    report['thermal_celsius']={}
    for sensor in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try:report['thermal_celsius'][sensor.parent.name]=int(sensor.read_text())/1000
        except (OSError,ValueError):pass
    commands={
        'os':['/usr/bin/cat','/etc/os-release'], 'kernel':['/usr/bin/uname','-a'],
        'python':['/usr/bin/python3','--version'],
        'packages':['/usr/bin/dpkg-query','-W','network-manager','apache2','nftables','dnsmasq-base','python3','openssl','docker.io'],
        'ark_services':['/usr/bin/systemctl','list-units','--all','--plain','--no-pager','dataark*'],
        'uptime':['/usr/bin/uptime'], 'memory':['/usr/bin/free','-h'],
        'storage':['/usr/bin/df','-hT'], 'mounts':['/usr/bin/findmnt','-o','TARGET,SOURCE,FSTYPE,OPTIONS'],
        'failed_services':['/usr/bin/systemctl','--failed','--no-pager'],
        'services':['/usr/bin/systemctl','show','dataark','apache2','dataark-portal-dns','dataark-pass-through','dataark-portal-monitor','dataark-wifi-roles','-p','Id','-p','ActiveState','-p','SubState','-p','Result'],
        'timers':['/usr/bin/systemctl','list-timers','--all','--no-pager'],
        'addresses':['/usr/sbin/ip','-brief','address'], 'routes':['/usr/sbin/ip','route','show','table','all'],
        'wifi':['/usr/sbin/iw','dev'],
        'connections':['/usr/bin/nmcli','-f','NAME,UUID,TYPE,DEVICE','connection','show','--active'],
        'devices':['/usr/bin/nmcli','device','status'],
        'firewall':['/usr/sbin/nft','list','ruleset'],
        'kernel_errors':['/usr/bin/journalctl','-k','-p','warning','-n','80','--no-pager','-o','short-iso'],
    }
    for name,args in commands.items():report[name]=command(args)
    report['service_journal']=command(['/usr/bin/journalctl','-u','dataark','-u','apache2','-u','dataark-portal-dns','-u','dataark-pass-through','-u','dataark-portal-monitor','-u','dataark-wifi-roles','-u','dataark-wifi-rollback','-u','dataark-usage','-u','NetworkManager','-n','180','--no-pager','-o','short-iso'],48000)
    report['application_events']=tail('/var/lib/ark/events.log',36000)
    report['portal_debug']=tail('/var/log/dataark-portal-monitor/events.log',36000)
    report['portal_debug_previous']=tail('/var/log/dataark-portal-monitor/events.log.1',18000)
    report['apache_errors']=tail('/var/log/apache2/error.log',12000)
    library=api('library')
    report['library']={k:library.get(k) for k in ('storage_ready','free_bytes','progress')}
    report['library']['telemetry_error']=library.get('error')
    report['library']['counts']={key:None if library.get('error') else len(library.get(key,[])) for key in ('installed','pending','removed')}
    report['library']['attention']=[{'id':row.get('id'),'title':row.get('title'),'update':row.get('update')} for row in library.get('installed',[]) if (row.get('update') or {}).get('result')=='error' or (row.get('update') or {}).get('pending_change')][:30]
    # Sanitize structured messages too; never include environment or credential stores.
    return sanitize(report)

if __name__=='__main__':
    if os.geteuid()!=0 or len(sys.argv)!=1:raise SystemExit('Root-owned support helper only.')
    try:print(json.dumps({'ok':True,'report':collect()},ensure_ascii=False))
    except Exception:print(json.dumps({'ok':False,'error':'Diagnostics could not be collected. Check the Pi locally.'}))
