import json
from urllib.parse import urlsplit
from fastapi import APIRouter, Request, HTTPException
from starlette.concurrency import run_in_threadpool
from app.services.network_admin import authorized
from app.services.https_setup import public_status, invoke

router = APIRouter(prefix='/https',tags=['HTTPS setup'])

@router.get('/status')
def status(): return public_status()

async def authenticate(request):
    origin = request.headers.get('origin')
    if origin and (urlsplit(origin).scheme not in ('http','https') or urlsplit(origin).netloc != request.headers.get('host')):
        raise HTTPException(403,'Use HTTPS setup from this Ark’s own page')
    header = request.headers.get('authorization','')
    if len(header)>2048 or not await run_in_threadpool(authorized,header): raise HTTPException(401,'Enter the caretaker password')

@router.get('/setup')
async def details(request: Request):
    await authenticate(request)
    value = await run_in_threadpool(invoke,{'action':'details'})
    if not value['ok']: raise HTTPException(400,value.get('error','Cannot read HTTPS setup'))
    return value

@router.post('/setup')
async def setup(request: Request):
    await authenticate(request)
    if request.headers.get('content-type','').split(';')[0].lower()!='application/json': raise HTTPException(415,'JSON request required')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>4096: raise HTTPException(413,'Request too large')
    try: data=json.loads(raw)
    except (ValueError,UnicodeError): raise HTTPException(400,'Invalid JSON')
    value=await run_in_threadpool(invoke,data)
    if not value['ok']: raise HTTPException(400,value.get('error','HTTPS setup failed'))
    return value
