"""Container web/API adapter: content services, without host administration."""
from datetime import datetime,timezone
import json,os,socket,time
from pathlib import Path,PurePosixPath
import requests
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse,JSONResponse,StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.staticfiles import StaticFiles
from app.services.network_admin import authorized

STARTED=time.monotonic()
CAPABILITIES={'deployment':'container','network_mode':'lan','network_controls':False,'wifi':False,'hotspot':False,
    'network_management':False,'host_administration':False,'drive_management':False,
    'content_downloads':False,'community':True,'library_read_only':True}
api=FastAPI(title='Data Ark container API',root_path='/api',docs_url=None,redoc_url=None)

# Existing portable content services keep their routes and durable data formats.
from app.routers import community,callsigns,documentation,events,library,configuration,debug,source_check
for module in (community,callsigns,documentation,events,library,configuration,debug,source_check):api.include_router(module.router)

@api.middleware('http')
async def boundaries(request,call_next):
    # No client can spoof the reverse proxy's trusted peer header.
    request.scope['headers']=[(k,v) for k,v in request.scope['headers'] if k.lower()!=b'x-dataark-peer']
    path=request.scope['path'];root=request.scope.get('root_path','')
    if root and path.startswith(root):path=path[len(root):] or '/'
    allowed=(path.startswith('/community/') or path in ('/debug/on','/debug/off','/library/unlock','/configuration/validate','/container/reload','/sources/check'))
    if request.method not in ('GET','HEAD','OPTIONS') and not allowed:
        return JSONResponse({'detail':'This operation belongs to the Linux host. The container serves its mounted library read-only; manage media and software on the host.'},status_code=501)
    if request.method not in ('GET','HEAD','OPTIONS'):
        from urllib.parse import urlsplit
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):return JSONResponse({'detail':'Use this Ark’s own page.'},status_code=403)
    return await call_next(request)

def network_data():
    try:address=socket.gethostbyname(socket.gethostname())
    except OSError:address=''
    wired={'interface':'container','managed':False,'carrier':bool(address),'enabled':True,'state':'up','connected':bool(address),'ip':address,'gateway':''}
    return {'capabilities':CAPABILITIES,'ethernet':wired,'ethernet_interfaces':[wired],
        'wifi':{'interface':'','enabled':None,'state':'not_configured','connected':False,'ssid':None,'signal':{'dbm':None,'percent':None},'rate':None,'ip':'','gateway':''},
        'access_point':{'interface':'','enabled':False,'active':False,'state':'not_configured','ip':'','ssid':'','client_count':0,'clients':[]}}

def reader_state():
    try:return json.loads(Path('/var/lib/dataark/container/reader.json').read_text())
    except (OSError,ValueError):return {'archives':0}

def status_data():
    from app.services.resources import collect
    resources=collect();issues=[]
    try:
        rendered=json.loads(Path('/var/lib/dataark/container/rendered.json').read_text())
        if rendered.get('error'):issues.append('Public configuration reload failed; the previous library is retained')
    except (OSError,ValueError):pass
    if not Path('/mnt/storage').is_mount():issues.append('External library bind mount is unavailable')
    reader=reader_state();reader_ok=True
    if reader['archives']:
        try:
            with requests.get('http://127.0.0.1:8089/kiwix/',timeout=2) as r:reader_ok=r.status_code==200
        except requests.RequestException:reader_ok=False
        if not reader_ok:issues.append('Archive reader unavailable')
    services={'fastapi':'running','apache':'not_applicable','network_manager':'not_applicable','samba':'not_applicable','kiwix':'running' if reader['archives'] and reader_ok else 'not_applicable' if not reader['archives'] else 'unavailable'}
    return {'network':network_data(),'system':{'hostname':socket.gethostname(),'platform':'Data Ark container · '+os.uname().machine,'uptime':str(int(time.monotonic()-STARTED)//60)+' minutes (web process)'},
        'resources':resources,'services':services,'status':{'state':'degraded' if issues else 'ok','issues':issues,
        'health':{'state':'warning' if issues else 'ok','problems':[{'id':'system.container.'+str(i),'severity':'warning','message':s} for i,s in enumerate(issues)]},
        'debug':Path('/var/lib/ark/debug_status').exists(),'sync':'Idle','updated':datetime.now(timezone.utc).isoformat(timespec='seconds')}}

@api.get('/')
def root():return {'application':'Data Ark','deployment':'container','version':'1.0.0','status':'running'}
@api.get('/container/health')
def health():return {'state':'running','deployment':'container'}
@api.get('/container/capabilities')
def capabilities():return CAPABILITIES
@api.get('/status')
def status():return status_data()
@api.get('/network')
def network():return network_data()
@api.get('/network/admin/access')
def access():return {'protected':['container'],'known':True}
@api.get('/portal/upstream')
def upstream():
    from app.routers.portal import upstream_state
    return upstream_state()
@api.get('/about')
def about():return {'product':'Data Ark','deployment':'container','build':os.environ.get('DATAARK_REVISION','development'),'hostname':socket.gethostname(),'api':'v1'}
@api.get('/recipient/status')
def recipient():return {'setup_required':False,'network_mode':'lan'}
@api.get('/https/status')
def https():return {'available':False,'enabled':False,'phase':'host_managed','http_available':True}
@api.get('/library/changes')
def changes():
    from app.services.collection_changes import snapshot
    return snapshot()
@api.get('/integration/health')
@api.get('/integration-health')
def integration():
    data=status_data();issues=data['status']['issues']
    return {'schema_version':1,'state':'warning' if issues else 'ok','problem_count':len(issues),'problems':[{'id':'container.'+str(i),'severity':'warning','message':s} for i,s in enumerate(issues)],'capabilities':CAPABILITIES,'services':data['services'],'observed_at':data['status']['updated']}

@api.post('/container/reload')
async def reload(request:Request):
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):raise HTTPException(401,'Caretaker password required')
    Path('/var/lib/dataark/container/reload').touch()
    return {'message':'Configuration reload requested. No downloads started.'}

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
app.mount('/api',api)

@app.api_route('/kiwix/{path:path}',methods=['GET','HEAD'])
async def reader(path:str,request:Request):
    if not reader_state()['archives']:return HTMLResponse('<h1>No offline archives installed</h1><p>Copy configured ZIM archives onto the library drive, then reload the container library.</p><a href="/">Dashboard</a>')
    # Fixed loopback origin. Never forward credentials, cookies or proxy headers.
    from urllib.parse import quote
    url='http://127.0.0.1:8089/kiwix/'+quote(path,safe='/')
    if request.url.query:url+='?'+request.url.query
    session=requests.Session();session.trust_env=False
    try:
        response=await run_in_threadpool(session.request,request.method,url,headers={'Accept-Encoding':'identity',**{k:v for k,v in request.headers.items() if k.lower() in ('range','if-range','if-none-match','accept')}},stream=True,allow_redirects=False,timeout=(3,30))
    except requests.RequestException:
        session.close();raise HTTPException(503,'Archive reader is starting or needs attention') from None
    headers={k:v for k,v in response.headers.items() if k.lower() in ('content-type','content-length','content-range','accept-ranges','etag','last-modified','cache-control')}
    # requests streams decoded bytes. Do not attach an upstream compressed size
    # to a decoded body; HTTP chunk framing preserves streaming and byte ranges.
    if request.method!='HEAD':headers={k:v for k,v in headers.items() if k.lower()!='content-length'}
    if response.headers.get('Location'):
        location=response.headers['Location']
        if location.startswith('http://127.0.0.1:8089/'):location=location.removeprefix('http://127.0.0.1:8089')
        if location.startswith('/kiwix/'):headers['Location']=location
    if path=='' and request.method=='GET' and response.status_code==200:
        try:
            body=bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body)>2*1024**2:raise HTTPException(503,'Archive catalogue exceeds its response limit')
            page=body.decode('utf-8')
            from tools.configure_kiwix_catalogue import render
            try:page=render(page)
            except ValueError:pass
            return HTMLResponse(page)
        finally:response.close();session.close()
    def chunks():
        try:
            yield from response.iter_content(65536)
        finally:response.close();session.close()
    return StreamingResponse(chunks(),status_code=response.status_code,headers=headers)

def public_media_path(path,data):
    parts=PurePosixPath(path).parts
    if not parts or any(p.startswith('.') or p in ('bugout-drop','System Volume Information','$RECYCLE.BIN') for p in parts):return False
    policy=Path(__file__).resolve().parents[2]/'config/clone-policy.json'
    folders=[PurePosixPath(row['path']).parts for row in json.loads(policy.read_text())['public_directories']]
    if any(parts[:len(prefix)]==prefix for prefix in folders):return True
    return path in {a['relative_path'] for a in data.get('assets',[]) if not a.get('removed')}

class PublicLibrary(StaticFiles):
    async def get_response(self,path,scope):
        from app.services.manifest import load_manifest
        data=await run_in_threadpool(load_manifest,Path('/opt/dataark/dataark.yaml'))
        if not public_media_path(path,data):raise HTTPException(404,'Public library file not found')
        return await super().get_response(path,scope)

app.mount('/library-files',PublicLibrary(directory='/mnt/storage',html=True,check_dir=False),name='library-files')
app.mount('/',StaticFiles(directory='/var/www/html',html=True,check_dir=False),name='web')
