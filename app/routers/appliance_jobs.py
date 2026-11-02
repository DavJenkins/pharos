"""Authenticated browser controls for existing bounded copy/restore engines."""
import json,subprocess
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from app.services.network_admin import authorized
router=APIRouter(prefix='/appliance-jobs',tags=['Make another Ark'])

@router.get('/storage')
def storage_status():
    from tools.storage_workflows import STATE
    path=STATE/'status.json'
    try:value=json.loads(path.read_text())
    except FileNotFoundError:value={'phase':'idle','message':'No storage transition in progress.'}
    return {**value,'library_mounted':Path('/mnt/storage').is_mount()}

@router.get('/card-package')
def card_status():
    from tools.ready_card import STATE
    try:return json.loads((STATE/'status.json').read_text())
    except FileNotFoundError:return {'phase':'idle','message':'No card preparation package requested.'}

@router.get('/card-download')
async def card_download(request:Request):
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):raise HTTPException(401,'Enter the caretaker password')
    from tools.ready_card import STATE
    if card_status()['phase']!='ready':raise HTTPException(409,'Finish building the package first')
    path=STATE/'data-ark-card-preparation.zip'
    if not path.is_file():raise HTTPException(404,'Package is not available')
    return FileResponse(path,filename=path.name,media_type='application/zip',headers={'Cache-Control':'no-store'})

def invoke(data):
    try:
        result=subprocess.run(['/usr/bin/sudo','-n','--','/usr/local/libexec/dataark-appliance-jobs'],input=json.dumps(data),capture_output=True,text=True,timeout=120)
        value=json.loads(result.stdout)
        if not value.get('ok'):raise ValueError(value.get('error','Request failed'))
        return value
    except subprocess.TimeoutExpired:raise ValueError('Inspection timed out; check progress before retrying.') from None
    except (OSError,json.JSONDecodeError):raise ValueError('Install the Make another Ark helper first.') from None

@router.post('/action')
async def action(request:Request):
    origin=request.headers.get('origin')
    if origin and (urlsplit(origin).scheme not in ('http','https') or urlsplit(origin).netloc!=request.headers.get('host')):raise HTTPException(403,'Use this Ark’s own page')
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):raise HTTPException(401,'Enter the caretaker password')
    if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'JSON required')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>4096:raise HTTPException(413,'Request too large')
    try:
        data=json.loads(body)
        return await run_in_threadpool(invoke,data)
    except (ValueError,OSError) as e:raise HTTPException(409,str(e)) from None
