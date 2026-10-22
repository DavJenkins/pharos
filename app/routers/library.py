import json
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from app.services import library
from app.services.network_admin import authorized

router = APIRouter(prefix='/library', tags=['Library'])

@router.get('')
def inventory():
    return library.inventory()

@router.get('/catalogue')
def catalogue():
    return library.catalogue()

@router.post('/unlock')
async def unlock(request: Request):
    await check_password(request)
    return {'message':'Library management unlocked.'}

async def check_password(request: Request):
    if not await run_in_threadpool(authorized, request.headers.get('authorization','')[:2049]):
        raise HTTPException(401, 'Password not accepted. Use the Ark caretaker password used for network settings, rather than the Wi-Fi password or Pi login password.')

@router.post('/install')
async def install(request: Request):
    return await mutation(request,'install')

@router.post('/remove')
async def remove(request: Request):
    return await mutation(request,'remove')

@router.post('/restore')
async def restore(request: Request):
    return await mutation(request,'restore')

async def mutation(request: Request, action: str):
    await check_password(request)
    if request.headers.get('content-type','').split(';')[0] != 'application/json':
        raise HTTPException(415, 'JSON required')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>2048:
            raise HTTPException(413, 'Request too large')
    try:
        payload=json.loads(body)
        fields={'install':{'repository_id','release','bytes'},'remove':{'asset_id','relative_path','bytes'},'restore':{'asset_id'}}
        if not isinstance(payload,dict) or set(payload)!=fields[action]:
            raise ValueError('Invalid library request')
        if action!='install':
            payload['action']=action
        return await run_in_threadpool(library.install,payload)
    except (ValueError, OSError) as error:
        raise HTTPException(400,str(error)) from None
