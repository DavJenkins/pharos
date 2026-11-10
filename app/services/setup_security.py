"""Immediate, bounded first-owner setup alerts; no submitted credentials are retained."""
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timezone
import json,sqlite3,time,uuid,logging,socket,hashlib
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
STATE=Path('/var/lib/dataark/bugout/setup-security')
RETENTION_SECONDS=30*24*60*60
KINDS={'code_rejected','cooldown','setup_completed'}
@contextmanager
def database():
 if STATE.is_symlink() or (STATE/'events.sqlite3').is_symlink():raise OSError('Unexpected setup security symlink')
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 db=sqlite3.connect(STATE/'events.sqlite3',timeout=3);db.row_factory=sqlite3.Row
 try:
  db.execute('CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY,kind TEXT,created REAL,occurrences INTEGER DEFAULT 1,acknowledged INTEGER DEFAULT 0,delivered INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,next_try REAL DEFAULT 0)')
  db.execute('DELETE FROM alerts WHERE created<=?',(time.time()-RETENTION_SECONDS,))
  db.commit()
  yield db;db.commit()
 finally:db.close()
def integration():
 from app.services.bugout import integration as settings
 return settings()
def record(kind):
 if kind not in KINDS:raise ValueError('Unknown setup security event')
 now=time.time();key=('cooldown-'+str(int(now//60))) if kind=='cooldown' else uuid.uuid4().hex
 with database() as db:
  db.execute('INSERT INTO alerts(id,kind,created) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET occurrences=occurrences+1,acknowledged=0',(key,kind,now))
  db.execute('DELETE FROM alerts WHERE id IN (SELECT id FROM alerts ORDER BY created DESC LIMIT -1 OFFSET 1000)')
 logging.getLogger(__name__).warning('First-owner setup event: %s',kind)
 # Local evidence is committed before attempting any network delivery.
 deliver(key)
 return key
def snapshot():
 if not (STATE/'events.sqlite3').exists():return {'unacknowledged':0,'pending_delivery':0,'events':[],'pending_events':[]}
 with database() as db:
  rows=[dict(r) for r in db.execute('SELECT id,kind,created,occurrences,acknowledged,delivered FROM alerts ORDER BY created DESC LIMIT 100')]
  count=db.execute("SELECT coalesce(sum(occurrences),0) FROM alerts WHERE acknowledged=0 AND kind!='setup_completed'").fetchone()[0]
  pending=db.execute('SELECT count(*) FROM alerts WHERE delivered=0').fetchone()[0]
  pending_events=[dict(r) for r in db.execute('SELECT id,kind,created,occurrences FROM alerts WHERE delivered=0 ORDER BY created LIMIT 100')]
 return {'unacknowledged':count,'pending_delivery':pending,'events':rows,'pending_events':pending_events}
def acknowledge(ids):
 if not isinstance(ids,list) or len(ids)>100 or not all(isinstance(v,str) and len(v)<=80 for v in ids):raise ValueError('Choose the displayed events')
 with database() as db:db.executemany('UPDATE alerts SET acknowledged=1 WHERE id=?',[(v,) for v in ids])
def delivered(ids):
 if not isinstance(ids,list) or len(ids)>100 or not all(isinstance(v,str) and len(v)<=80 for v in ids):raise ValueError('Choose the displayed events')
 with database() as db:db.executemany('UPDATE alerts SET delivered=1 WHERE id=?',[(v,) for v in ids])
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def deliver(event_id=None):
 if not (STATE/'events.sqlite3').exists():return
 with database():pass  # Expire old messages even while HA is unconfigured/offline.
 cfg=integration();url=cfg.get('url','').rstrip('/');token=cfg.get('token');u=urlsplit(url)
 if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment or not token:return
 with database() as db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT * FROM alerts WHERE delivered=0 AND next_try<=? '+('AND id=? ' if event_id else '')+'ORDER BY created LIMIT 1',(time.time(),event_id) if event_id else (time.time(),)).fetchone()
  if row is not None:db.execute('UPDATE alerts SET next_try=? WHERE id=?',(time.time()+30,row['id']))
 if row is None:return
 host=socket.gethostname();when=datetime.fromtimestamp(row['created'],timezone.utc).isoformat(timespec='seconds')
 payload={'event_id':row['id'],'kind':row['kind'],'timestamp':when,'hostname':host,'occurrences':row['occurrences']}
 message={'code_rejected':'An incorrect first-owner setup code was submitted.','cooldown':'First-owner setup is rate-limited after incorrect code attempts.','setup_completed':'First-owner setup completed.'}[row['kind']]
 opener=build_opener(ProxyHandler({}),NoRedirect())
 try:
  for path,data in [('/api/events/dataark_setup_security',payload),('/api/services/persistent_notification/create',{'title':'Data Ark setup security','message':host+': '+message+' '+when,'notification_id':'dataark_setup_'+hashlib.sha256(host.encode()).hexdigest()[:12]})]:
   q=Request(url+path,data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
   with opener.open(q,timeout=2) as response:
    if response.status!=200:raise OSError('Delivery rejected')
  with database() as db:db.execute('UPDATE alerts SET delivered=1 WHERE id=?',(row['id'],))
 except Exception:
  with database() as db:db.execute('UPDATE alerts SET attempts=attempts+1,next_try=? WHERE id=?',(time.time()+min(300,5*2**min(row['attempts'],6)),row['id']))
  logging.getLogger(__name__).warning('Setup-security alert retained locally; Home Assistant delivery pending')
def safe_record(kind):
 try:return record(kind)
 except (OSError,ValueError,sqlite3.Error,RuntimeError):logging.getLogger(__name__).exception('Setup-security reporting failed')
