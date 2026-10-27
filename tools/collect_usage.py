#!/usr/bin/env python3
"""Aggregate local usage. Never persist visitor addresses, URLs or user agents."""
import fcntl,json,re,subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
STATE=Path('/var/lib/dataark/usage/state.json')
PUBLIC=Path('/mnt/storage/usage.json')
LOG=Path('/var/log/apache2/access.log')
LINE=re.compile(r'^([^ ]+) .*?\[([^]]+)\] "(GET|HEAD) ([^ ]+) HTTP/[^"]+" (\d{3}) (\d+|-) ')

def classify(line):
 m=LINE.match(line)
 if not m or m[1] in ('127.0.0.1','::1') or m[3]!='GET' or not 200<=int(m[5])<300:return None
 try:path=urlsplit(m[4]).path
 except ValueError:return None
 if path.startswith(('/api/','/assets/','/generate_','/gen_')) or path.endswith(('.json','.js','.css','.ico','.woff','.woff2')):return None
 if path in ('/','/index.html'):group='Dashboard'
 elif path.startswith('/library-files/'):
  parts=path.split('/');group=parts[2] if len(parts)>3 and parts[2] in {'family-resources','forms','resilience','civic-reference','curriculum','maps','callsigns','radio-study','kiwix-viewer','vehicle-manuals','legal','contracts'} else 'Other files'
 elif path.startswith('/docs/'):group='Documentation'
 elif path.endswith(('.html','.pdf','.epub','.zim','.zip','.docx','.txt')):group='Other pages and downloads'
 else:return None
 try:dt=datetime.strptime(m[2],'%d/%b/%Y:%H:%M:%S %z').astimezone(timezone.utc)
 except ValueError:return None
 return dt,int(m[6]) if m[6]!='-' else 0,group

def empty():return {'opens':0,'bytes':0,'hotspot_peak':None,'samples':0,'collections':{}}
def add(bucket,size,group):
 bucket['opens']+=1;bucket['bytes']+=size;bucket['collections'][group]=bucket['collections'].get(group,0)+1

def consume(state,log,now):
 paths=[log.with_name(log.name+'.1'),log]
 pointer=state.get('log');started=state['started_at']
 for path in paths:
  if not path.exists():continue
  stat=path.stat();key=str(stat.st_dev)+':'+str(stat.st_ino)
  if not pointer:
   if path==log:state['log']={'key':key,'offset':stat.st_size}
   continue
  if key==pointer['key']:offset=pointer['offset'] if pointer['offset']<=stat.st_size else 0
  elif path==log:offset=0
  else:continue
  with path.open('rb') as stream:
   stream.seek(offset);data=stream.read(8*1024*1024)
  end=data.rfind(b'\n')+1
  for line in data[:end].decode('utf-8',errors='replace').splitlines():
   item=classify(line)
   if not item:continue
   dt,size,group=item
   if dt.isoformat()<started or dt>now+timedelta(minutes=5) or dt<now-timedelta(days=365):continue
   day=dt.strftime('%Y-%m-%d');hour=dt.strftime('%Y-%m-%dT%H:00:00Z')
   add(state['daily'].setdefault(day,empty()),size,group)
   if dt>=now-timedelta(days=30):add(state['hourly'].setdefault(hour,empty()),size,group)
  state['log']={'key':key,'offset':offset+end}
  if offset+end<stat.st_size:return

def command(args):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=5)
  return p.stdout if p.returncode==0 else None
 except (OSError,subprocess.TimeoutExpired):return None

def sample():
 stations=command(['iw','dev','wlan0','station','dump'])
 sockets=command(['ss','-Htn','state','established'])
 result={'hotspot_devices':None if stations is None else sum(x.startswith('Station ') for x in stations.splitlines()),'ssh_connections':None,'desktop_connections':None,'terminal_connections':None}
 if sockets is not None:
  for name in ['ssh_connections','desktop_connections','terminal_connections']:result[name]=0
  for line in sockets.splitlines():
   fields=line.split()
   if len(fields)<4:continue
   local,peer=fields[2:4]
   if peer.startswith(('127.0.0.1:','[::1]:')):continue
   port=local.rsplit(':',1)[-1]
   for name,ports in [('ssh_connections',{'22'}),('desktop_connections',{'5900','5901'}),('terminal_connections',{'4200'})]:
    if port in ports:result[name]+=1
 return result

def write(path,value,mode):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,separators=(',',':'))+'\n',encoding='utf-8');temp.chmod(mode);temp.replace(path)

def collect(state,log,now,current):
 consume(state,log,now)
 for name,key in [('daily',now.strftime('%Y-%m-%d')),('hourly',now.strftime('%Y-%m-%dT%H:00:00Z'))]:
  bucket=state[name].setdefault(key,empty());bucket['samples']+=1
  count=current['hotspot_devices']
  if count is not None:bucket['hotspot_peak']=max(bucket['hotspot_peak'] or 0,count)
 for name,days in [('daily',365),('hourly',30)]:
  cutoff=(now-timedelta(days=days)).strftime('%Y-%m-%d' if name=='daily' else '%Y-%m-%dT%H:00:00Z')
  state[name]={key:value for key,value in state[name].items() if key>=cutoff}
 state['updated_at']=now.isoformat();state['current']=current
 return {k:v for k,v in state.items() if k!='log'}

def main():
 STATE.parent.mkdir(parents=True,exist_ok=True);STATE.parent.chmod(0o700)
 with (STATE.parent/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  now=datetime.now(timezone.utc)
  state=json.loads(STATE.read_text()) if STATE.exists() else {'started_at':now.isoformat(),'daily':{},'hourly':{}}
  public=collect(state,LOG,now,sample());write(STATE,state,0o600)
  if Path('/mnt/storage').is_mount():write(PUBLIC,public,0o644)
if __name__=='__main__':main()
