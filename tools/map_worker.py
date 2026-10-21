#!/usr/bin/env python3
"""Collect configured Massachusetts reference maps; never participates in bugout."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import load_manifest, atomic_write, inside

STATE = Path('/var/lib/dataark/maps')
MASS = 'https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/'
TOWNS = 'https://services1.arcgis.com/hGdibHYSPO59RG1h/ArcGIS/rest/services/Massachusetts_Municipalities_Hosted/FeatureServer/0/query'
PARCELS = 'https://www.mass.gov/doc/massgis-parcel-data-download-links-table/download'
TNM = 'https://tnmaccess.nationalmap.gov/api/v1/products'
SOURCES = {
 'flood': ('Flood hazards', 'MassGIS / FEMA', 'https://www.mass.gov/info-details/massgis-data-fema-national-flood-hazard-layer'),
 'parcels': ('Property boundaries', 'MassGIS', 'https://www.mass.gov/info-details/massgis-data-property-tax-parcels'),
 'topographic': ('Topographic maps', 'USGS', 'https://www.usgs.gov/programs/national-geospatial-program/us-topo-maps-america')}


def settings(data):
    cfg = data.get('maps', {})
    if not isinstance(cfg, dict) or set(cfg)-{'enabled','refresh_days','reserve_gib','max_run_gib','sources'}:
        raise ValueError('maps accepts enabled, refresh_days, reserve_gib, max_run_gib and sources')
    if type(cfg.get('enabled',False)) is not bool:
        raise ValueError('maps.enabled must be true or false')
    for key, default, high in [('refresh_days',30,3650),('reserve_gib',10,1024),('max_run_gib',8,1024)]:
        if type(cfg.get(key,default)) is not int or not 1 <= cfg.get(key,default) <= high:
            raise ValueError('Invalid maps.'+key)
    sources=cfg.get('sources',list(SOURCES))
    if not isinstance(sources,list) or not sources or any(not isinstance(v,str) or v not in SOURCES for v in sources) or len(sources)!=len(set(sources)):
        raise ValueError('maps.sources must contain unique supported source names')
    if cfg.get('enabled') and data.get('geography',{}).get('state',{}).get('code') != 'MA':
        raise ValueError('The map adapters currently support Massachusetts only')
    return cfg


def small(url):
    with urlopen(Request(url),timeout=30) as response:
        value=response.read(16*1024**2+1)
    if len(value)>16*1024**2:
        raise ValueError('Source metadata exceeds 16 MiB')
    return value


def json_data(url):
    value=json.loads(small(url))
    if value.get('error') or value.get('errors'):
        raise ValueError('Source returned an error')
    return value


def county_towns(data):
    response=json_data(TOWNS+'?'+urlencode({'where':'1=1','outFields':'TOWN,TOWN_ID,COUNTY,FIPS_STCO','returnGeometry':'false','f':'json'}))
    if response.get('exceededTransferLimit'):
        raise ValueError('Municipality response was truncated')
    wanted={c['name'].casefold():c['name'] for c in data['geography']['counties']}
    selected={}
    for feature in response.get('features',[]):
        a=feature['attributes']
        name=a['COUNTY'].strip().casefold()
        if name in wanted:
            selected[int(a['TOWN_ID'])]={'name':a['TOWN'],'county':wanted[name],'fips':str(a['FIPS_STCO']).zfill(5)}
    missing=set(wanted)-{v['county'].casefold() for v in selected.values()}
    if missing:
        raise ValueError('No municipality metadata for: '+', '.join(sorted(missing)))
    return selected


def parcel_rows(blob):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if sum(i.file_size for i in archive.infolist())>32*1024**2:
            raise ValueError('Parcel table expands beyond limit')
        strings=[''.join(t.text or '' for t in x.findall('.//m:t',ns)) for x in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        rows=[]
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//m:row',ns):
            values={}
            for cell in row:
                column=re.sub(r'\d','',cell.attrib['r'])
                value=cell.findtext('m:v','',ns)
                values[column]=strings[int(value)] if cell.get('t')=='s' else value
            rows.append(values)
    if not rows or rows[0].get('B')!='Town ID' or rows[0].get('C')!='Shapefile Download URL':
        raise ValueError('Parcel table columns changed')
    return rows[1:]


def parcel_url(value):
    parsed=urlsplit(value)
    if parsed.hostname!='download.massgis.digital.mass.gov' or not re.fullmatch(r'/shapefiles/l3parcels/[A-Za-z0-9_.-]+\.zip',parsed.path):
        raise ValueError('Unexpected parcel download address')
    return MASS+parsed.path.lstrip('/')


def latest_topos(items):
    chosen={}
    for item in items:
        address=item.get('downloadURL','')
        parsed=urlsplit(address)
        if parsed.scheme!='https' or parsed.hostname!='prd-tnm.s3.amazonaws.com' or not parsed.path.startswith('/StagedProducts/Maps/USTopo/PDF/') or not parsed.path.endswith('.pdf'):
            raise ValueError('Unexpected USGS download address')
        box=item['boundingBox']
        key=tuple(box[k] for k in ('minX','minY','maxX','maxY'))
        if key not in chosen or (item['publicationDate'],item.get('lastUpdated','')) > (chosen[key]['publicationDate'],chosen[key].get('lastUpdated','')):
            chosen[key]=item
    return list(chosen.values())


def discover(data):
    cfg=settings(data); towns=county_towns(data); items=[]
    sources=cfg.get('sources',list(SOURCES))
    if 'flood' in sources:
        items.append({'id':'ma-nfhl','group':'flood','title':'Massachusetts flood hazards (statewide published coverage)',
            'url':MASS+'shapefiles/state/nfhl.zip','path':'flood/massachusetts-nfhl.zip','format':'GIS ZIP'})
    if 'parcels' in sources:
        matched=set()
        for row in parcel_rows(small(PARCELS)):
            if not row.get('B','').isdigit() or int(row['B']) not in towns:
                continue
            number=int(row['B']);town=towns[number];matched.add(number)
            items.append({'id':f'parcels-{number}','group':'parcels','title':town['name']+' — '+town['county']+' County',
                'url':parcel_url(row['C']),'path':f'parcels/town-{number:03d}.zip','format':'GIS ZIP','edition':row.get('E','')})
        if matched!=set(towns):
            raise ValueError('Parcel table is missing selected municipalities')
    if 'topographic' in sources:
        products=[]
        for fips in sorted({v['fips'] for v in towns.values()}):
            offset=0
            while True:
                response=json_data(TNM+'?'+urlencode({'datasets':'US Topo','polyType':'county','polyCode':fips,'max':100,'offset':offset,'outputFormat':'JSON'}))
                batch=response.get('items',[]);products.extend(batch);offset+=len(batch)
                if offset>=response['total']:break
                if not batch or offset>5000:raise ValueError('USGS pagination incomplete')
        if not products:raise ValueError('USGS returned no maps for the configured counties')
        for product in latest_topos(products):
            box=product['boundingBox'];key=hashlib.sha256(json.dumps(box,sort_keys=True).encode()).hexdigest()[:16]
            items.append({'id':'topo-'+key,'group':'topographic','title':product['title'],
                'url':product['downloadURL'],'path':'topographic/'+key+'.pdf','format':'PDF','edition':product['publicationDate']})
    return items


def transfer(item, target, old, reserve, budget, volume=None):
    headers={}
    if target.is_file() and old.get('url')==item['url']:
        if old.get('etag'):headers['If-None-Match']=old['etag']
        if old.get('modified'):headers['If-Modified-Since']=old['modified']
    try:
        response=urlopen(Request(item['url'],headers=headers),timeout=30)
    except HTTPError as error:
        if error.code==304 and target.is_file():return dict(old,checked=time.time(),error=None),0
        raise
    partial=target.with_name('.'+target.name+'.part')
    if partial.is_symlink() or target.is_symlink():
        response.close()
        raise ValueError('Unsafe map destination')
    count=0; digest=hashlib.sha256();limit=min(budget['remaining'],2*1024**3)
    try:
        with response, partial.open('wb') as stream:
            length=int(response.headers.get('Content-Length',0))
            if length>limit:raise ValueError('Download exceeds remaining run or 2 GiB file limit')
            if length and shutil.disk_usage(target.parent).free-length<reserve:raise ValueError('Insufficient storage reserve')
            while True:
                block=response.read(1024**2)
                if not block:break
                count+=len(block)
                budget['remaining']-=len(block)
                if volume is not None and not volume.is_mount():raise ValueError('Content SSD disconnected')
                if count>limit or shutil.disk_usage(target.parent).free-len(block)<reserve:raise ValueError('Download budget or storage reserve reached')
                stream.write(block);digest.update(block)
            stream.flush();os.fsync(stream.fileno())
            if not count or (length and count!=length):raise ValueError('Incomplete download')
            meta={'url':item['url'],'etag':response.headers.get('ETag'),'modified':response.headers.get('Last-Modified'),
                  'bytes':count,'sha256':digest.hexdigest(),'checked':time.time(),'saved':time.time(),'error':None}
        if item['format']=='PDF':
            with partial.open('rb') as stream:
                if stream.read(5)!=b'%PDF-':raise ValueError('Expected a PDF, received another response')
        else:
            with zipfile.ZipFile(partial) as archive:
                if not archive.namelist() or sum(x.file_size for x in archive.infolist())>4*1024**3:raise ValueError('Invalid or oversized ZIP contents')
                if archive.testzip():raise ValueError('ZIP integrity check failed')
        os.replace(partial,target)
        return meta,count
    finally:
        partial.unlink(missing_ok=True)


def publish(folder, items, state, coverage):
    def stamp(value):
        return datetime.fromtimestamp(value).astimezone().strftime('%b %d, %Y at %I:%M %p %Z') if value else 'Not yet downloaded'
    for group in [None]+list(SOURCES):
        rows=[]
        for item in items:
            if group and item['group']!=group:continue
            status=state.get('files',{}).get(item['id'],{})
            target=inside(folder,item['path']);available=target.is_file()
            rel=Path(item['path']).name if group else item['path']
            link=('<a href="'+html.escape(rel,quote=True)+'">'+('Open PDF' if item['format']=='PDF' else 'Download GIS ZIP')+'</a>') if available else 'Pending download'
            rows.append('<li><strong>'+html.escape(item['title'])+'</strong> '+link+'<br>Edition: '+html.escape(item.get('edition','See publisher metadata'))+
                ' · Saved: '+stamp(status.get('saved'))+' · Checked: '+stamp(status.get('checked'))+
                (' · '+html.escape(status['error']) if status.get('error') else '')+'</li>')
        for source,error in state.get('group_errors',{}).items():
            if not group or group==source:rows.append('<li>Source metadata error ('+html.escape(source)+'): '+html.escape(error)+'</li>')
        title=SOURCES[group][0] if group else 'Local maps'
        links=' '.join('<a href="'+('index.html' if group==k else ('../' if group else '')+k+'/index.html')+'">'+v[0]+'</a>' for k,v in SOURCES.items())
        attribution=' '.join('<a href="'+v[2]+'">'+v[1]+' source information (online)</a>' for k,v in SOURCES.items() if not group or k==group)
        page='<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+title+'</title><style>body{max-width:65em;margin:2em auto;padding:1em;font:16px system-ui;background:#f6f3e8;color:#243849}li{margin:1em 0}a{color:#155a78}</style><h1>'+title+'</h1><p>'+html.escape(coverage)+'</p><nav>'+links+'</nav><p>PDFs can be read offline. ZIP archives contain GIS data and require compatible GIS software; no interactive map viewer is included. Parcel lines are not a survey. Flood data shows published hazards, not live flooding; missing mapping does not mean no risk.</p><p>'+attribution+'</p><p>Collection: '+html.escape(state.get('status','Pending'))+'</p><ul>'+''.join(rows)+'</ul>'
        dest=folder/group if group else folder;dest.mkdir(exist_ok=True)
        atomic_write(dest/'index.html',page.encode('utf-8'))
    atomic_write(folder/'status.json',json.dumps(state,indent=2).encode())


def run(data, force=False):
    cfg=settings(data)
    if not cfg.get('enabled'):return
    root=Path(data['system']['base_mount'])
    if not root.is_mount():raise ValueError('Content SSD is not mounted')
    folder=inside(root,'maps');folder.mkdir(exist_ok=True)
    for group in SOURCES:inside(folder,group).mkdir(exist_ok=True)
    path=STATE/'state.json'
    state=json.loads(path.read_text()) if path.exists() else {'files':{}}
    interval=cfg.get('refresh_days',30)*86400
    signature=hashlib.sha256(json.dumps({'geography':data['geography'],'sources':cfg.get('sources',list(SOURCES))},sort_keys=True).encode()).hexdigest()
    if state.get('signature')!=signature:
        state['items']=[];state['group_checked']={};state['group_errors']={};state['signature']=signature
    for group in cfg.get('sources',list(SOURCES)):
        if not force and time.time()-state.setdefault('group_checked',{}).get(group,0)<interval:continue
        try:
            scoped=dict(data,maps=dict(cfg,sources=[group]))
            found=discover(scoped)
            state['items']=[i for i in state.get('items',[]) if i['group']!=group]+found
            state['group_checked'][group]=time.time()
            state.setdefault('group_errors',{}).pop(group,None)
        except Exception as error:
            state.setdefault('group_errors',{})[group]=str(error)
    items=state.get('items',[])
    coverage=data['geography']['state']['name']+': '+', '.join(c['name']+' County' for c in data['geography']['counties'])+'; flood archive is statewide.'
    budget={'remaining':cfg.get('max_run_gib',8)*1024**3}
    state['status']='Checking and downloading';state['updated']=time.time()
    atomic_write(path,json.dumps(state).encode());publish(folder,items,state,coverage)
    for item in items:
        old=state['files'].get(item['id'],{});target=inside(folder,item['path'])
        if not force and not old.get('error') and target.is_file() and old.get('url')==item['url'] and time.time()-old.get('checked',0)<interval:continue
        try:
            result,used=transfer(item,target,old,cfg.get('reserve_gib',10)*1024**3,budget,root)
            state['files'][item['id']]=result
        except Exception as error:
            state['files'][item['id']]=dict(old,error=str(error))
        atomic_write(path,json.dumps(state).encode());publish(folder,items,state,coverage)
        if budget['remaining']<=0:break
    errors=bool(state.get('group_errors')) or any(state['files'].get(i['id'],{}).get('error') or not inside(folder,i['path']).is_file() for i in items)
    state['status']='Metadata needs attention: '+', '.join(state['group_errors']) if state.get('group_errors') else 'Some downloads pending or failed' if errors else 'Up to date'
    state['updated']=time.time();atomic_write(path,json.dumps(state).encode());publish(folder,items,state,coverage)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',action='store_true');parser.add_argument('--check-now',action='store_true');parser.add_argument('--initialize',action='store_true')
    args=parser.parse_args();data=load_manifest(ROOT/'dataark.yaml')
    if args.initialize:
        root=Path(data['system']['base_mount'])
        if not root.is_mount():raise ValueError('Content SSD is not mounted')
        folder=inside(root,'maps');folder.mkdir(exist_ok=True)
        if not (folder/'index.html').exists():
            publish(folder,[],{'status':'Awaiting first collection'},data['geography']['state']['name'])
        return
    if args.plan:
        items=discover(data)
        print(json.dumps({'coverage':data['geography'],'counts':{k:sum(i['group']==k for i in items) for k in SOURCES},'items':items},indent=2));return
    import fcntl
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'worker.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        import signal
        def stop(signum, frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,stop)
        try:
            run(data,args.check_now)
        except KeyboardInterrupt:
            path=STATE/'state.json'
            state=json.loads(path.read_text()) if path.exists() else {'files':{}}
            state['status']='Interrupted; incomplete files retry on the next run';state['updated']=time.time()
            atomic_write(path,json.dumps(state).encode())
            root=Path(data['system']['base_mount'])
            if root.is_mount():publish(inside(root,'maps'),state.get('items',[]),state,data['geography']['state']['name'])
            raise SystemExit(1)


if __name__=='__main__':main()
