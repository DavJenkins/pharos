"""Public readiness and authenticated bugout commands."""
import json
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services import bugout as service
from app.services.network_admin import authorized

router = APIRouter(prefix='/bugout', tags=['Bugout'])


@router.get('/state')
async def state():
    try:
        value = await run_in_threadpool(service.readiness)
        return JSONResponse(value, headers={'Cache-Control':'no-store'})
    except (OSError, ValueError, RuntimeError):
        return {'configured':True,'ready':False,'reason':'Bugout configuration or state unavailable','tasks':[],'operation':None}


async def authenticated(request, admin_only=False):
    header = request.headers.get('authorization','')
    if len(header) <= 2048:
        if await run_in_threadpool(authorized,header):
            return 'ark'
        if not admin_only and await run_in_threadpool(service.ha_authorized,header):
            return 'home_assistant'
    if admin_only:
        raise HTTPException(401,'Data Ark network administration authentication failed. Check the administration password at the top of this form.')
    raise HTTPException(401,'Administration password or a valid integration token required')


async def body(request):
    if request.headers.get('content-type','').split(';')[0].strip() != 'application/json':
        raise HTTPException(415,'JSON required')
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 4096:
            raise HTTPException(413,'Request too large')
    try:
        value = json.loads(data)
        if not isinstance(value,dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise HTTPException(400,'Invalid JSON') from None


@router.post('/trigger')
async def trigger(request: Request):
    origin = await authenticated(request)
    value = await body(request)
    if set(value) != {'operation_id'}:
        raise HTTPException(400,'Supply only operation_id; task configuration is server-side')
    try:
        return await run_in_threadpool(service.start,value['operation_id'],origin)
    except ValueError as error:
        raise HTTPException(409,str(error)) from None
    except (OSError, RuntimeError):
        raise HTTPException(503,'Bugout worker or state unavailable') from None


@router.post('/credentials/{task_id}')
async def credentials(task_id: str, request: Request):
    await authenticated(request, admin_only=True)
    value = await body(request)
    try:
        await run_in_threadpool(service.save_credential,task_id,value)
    except ValueError as error:
        raise HTTPException(400,str(error)) from None
    except (OSError, RuntimeError):
        raise HTTPException(503,'Private credential storage unavailable') from None
    return {'ok':True}


@router.post('/sync')
async def sync(request: Request):
    origin = await authenticated(request, admin_only=True)
    value = await body(request)
    if set(value) != {'operation_id'}:
        raise HTTPException(400,'Supply only operation_id')
    try:
        return await run_in_threadpool(service.start,value['operation_id'],origin,'prefetch')
    except ValueError as error:
        raise HTTPException(409,str(error)) from None
    except (OSError, RuntimeError):
        raise HTTPException(503,'Sync worker or state unavailable') from None


@router.post('/cancel')
async def cancel(request: Request):
    await authenticated(request)
    value = await body(request)
    if set(value) != {'operation_id','continue_updates'} or not isinstance(value['operation_id'],str):
        raise HTTPException(400,'Supply operation_id and continue_updates')
    try:
        return await run_in_threadpool(service.cancel,value['operation_id'],value['continue_updates'])
    except ValueError as error:
        raise HTTPException(409,str(error)) from None
    except (OSError, RuntimeError):
        raise HTTPException(503,'Bugout state unavailable') from None


@router.post('/credentials/{task_id}/test')
async def test_credentials(task_id: str, request: Request):
    await authenticated(request, admin_only=True)
    value = await body(request)
    try:
        result = await run_in_threadpool(service.test_credential,task_id,value)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    except ValueError as error:
        raise HTTPException(400,str(error)) from None
    except (OSError, RuntimeError):
        raise HTTPException(503,'Credential test unavailable') from None
