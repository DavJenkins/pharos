"""Read-only local FCC callbook with approximate mailing-ZIP proximity."""
import json,math,re,sqlite3
from pathlib import Path
from fastapi import APIRouter,HTTPException,Query
router=APIRouter(prefix='/callsigns',tags=['Callsigns'])
DATABASE=Path('/mnt/storage/civic-reference/callsigns.sqlite')
def connect():
 if not DATABASE.is_file():raise HTTPException(503,'Callsign database is not installed. A caretaker can rebuild it with tools/install_callsigns.py.')
 db=sqlite3.connect('file:'+str(DATABASE)+'?mode=ro',uri=True,timeout=3);db.row_factory=sqlite3.Row
 return db
def grid_center(grid):
 g=grid.strip().upper()
 if not re.fullmatch(r'[A-R]{2}(?:[0-9]{2}(?:[A-X]{2}(?:[0-9]{2})?)?)?',g):raise ValueError('Use a 2, 4, 6 or 8 character Maidenhead grid locator.')
 lon=(ord(g[0])-65)*20-180;lat=(ord(g[1])-65)*10-90;w,h=20,10
 if len(g)>=4:lon+=int(g[2])*2;lat+=int(g[3]);w,h=2,1
 if len(g)>=6:lon+=(ord(g[4])-65)/12;lat+=(ord(g[5])-65)/24;w,h=1/12,1/24
 if len(g)>=8:lon+=int(g[6])/120;lat+=int(g[7])/240;w,h=1/120,1/240
 return lat+h/2,lon+w/2
def distance(lat1,lon1,lat2,lon2):
 a,b=math.radians(lat1),math.radians(lat2);x=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(math.radians(lon2-lon1)/2)**2
 return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,x))))
def bearing(lat1,lon1,lat2,lon2):
 if distance(lat1,lon1,lat2,lon2)<1e-6:return None
 a,b=math.radians(lat1),math.radians(lat2);dl=math.radians(lon2-lon1)
 return (math.degrees(math.atan2(math.sin(dl)*math.cos(b),math.cos(a)*math.sin(b)-math.sin(a)*math.cos(b)*math.cos(dl)))+360)%360
@router.get('/metadata')
def metadata():
 db=connect()
 try:return json.loads(db.execute('SELECT json FROM metadata').fetchone()[0])
 finally:db.close()
@router.get('/search')
def search(q:str=Query('',max_length=80),mode:str=Query('callsign',pattern='^(callsign|name)$'),state:str=Query('',max_length=2),city:str=Query('',max_length=60),grid:str=Query('',max_length=8),radius_km:float=Query(50,ge=1,le=1000),active:bool=True):
 q=q.strip();state=state.strip().upper();city=city.strip();grid=grid.strip()
 if not(q or grid or city):raise HTTPException(400,'Enter a callsign, name, city or grid locator.')
 if state and not re.fullmatch('[A-Z]{2}',state):raise HTTPException(400,'Use a two-letter state code.')
 db=connect()
 try:
  where=[];args=[];joins='';order='l.callsign,l.id';center=None
  if active:where.append("l.status='A'")
  if q and mode=='callsign':
   if not re.fullmatch('[A-Za-z0-9/]{1,20}',q):raise HTTPException(400,'Use letters, digits or / for a callsign prefix.')
   q=q.upper();where.append('l.callsign>=? AND l.callsign<?');args.extend([q,q+'~'])
  elif q:
   words=re.findall(r'[^\W_]+',q,re.UNICODE)
   if not words:raise HTTPException(400,'Enter a name containing letters or numbers.')
   joins+=' JOIN names ON names.rowid=l.rowid';where.append('names MATCH ?');args.append(' AND '.join('"'+w+'"*' for w in words))
  if state:where.append('l.state=?');args.append(state)
  if city:where.append("upper(l.city) LIKE ? ESCAPE '\\'");args.append(city.upper().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
  if grid:
   try:center=grid_center(grid)
   except ValueError as e:raise HTTPException(400,str(e))
   nearby=[]
   for z in db.execute('SELECT zip,lat,lon FROM zcta WHERE lat BETWEEN ? AND ?',(center[0]-radius_km/110,center[0]+radius_km/110)):
    d=distance(*center,z['lat'],z['lon'])
    if d<=radius_km:nearby.append((z['zip'],d,bearing(*center,z['lat'],z['lon'])))
   db.execute('CREATE TEMP TABLE nearby(zip TEXT PRIMARY KEY,distance_km REAL,bearing_true REAL)');db.executemany('INSERT INTO nearby VALUES(?,?,?)',nearby);joins+=' JOIN nearby n ON n.zip=l.zip';order='n.distance_km,l.callsign,l.id'
  cols='l.callsign,l.status,l.service,l.grant_date,l.expires,l.cancelled,l.name,l.city,l.state,l.zip'+(',n.distance_km,n.bearing_true' if grid else '')
  rows=[dict(r) for r in db.execute('SELECT '+cols+' FROM licenses l'+joins+' WHERE '+' AND '.join(where or ['1=1'])+' ORDER BY '+order+' LIMIT 101',args)]
  return {'results':rows[:100],'truncated':len(rows)>100,'grid_center':{'latitude':center[0],'longitude':center[1]} if center else None,'proximity_basis':'Approximate Census ZCTA point for licensee mailing ZIP; not station position.' if grid else None}
 finally:db.close()
