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

@router.post('/install')
async def install(request: Request):
    if not await run_in_threadpool(authorized, request.headers.get('authorization','')[:2049]):
        raise HTTPException(401, 'Enter the Ark administration password used for network settings.')
    if request.headers.get('content-type','').split(';')[0] != 'application/json':
        raise HTTPException(415, 'JSON required')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>2048:
            raise HTTPException(413, 'Request too large')
    try:
        payload=json.loads(body)
        if not isinstance(payload,dict) or set(payload)!={'repository_id','release','bytes'}:
            raise ValueError('Invalid library request')
        return await run_in_threadpool(library.install,payload)
    except (ValueError, OSError) as error:
        raise HTTPException(400,str(error)) from None
