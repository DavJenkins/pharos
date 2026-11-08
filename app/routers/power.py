"""Caretaker-only, explicitly confirmed appliance power controls."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from app.services.network_admin import authorized, invoke

router=APIRouter(prefix='/system/power',tags=['System'])

def available():
    return Path('/run/systemd/system').is_dir() and not Path('/.dockerenv').exists() and not Path('/run/.containerenv').exists()

@router.get('')
def status():
    return {'available':available()}

@router.post('')
async def control(request:Request):
    header=request.headers.get('authorization','')
    if len(header)>2048 or not await run_in_threadpool(authorized,header):
        raise HTTPException(401,'Caretaker password required.')
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise HTTPException(415,'JSON request required.')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>256:raise HTTPException(413,'Request too large.')
    try:data=json.loads(body)
    except (ValueError,UnicodeError):raise HTTPException(400,'Invalid JSON.') from None
    if not isinstance(data,dict) or set(data)!={'operation','confirmed'} or data['operation'] not in ('restart','shutdown') or data['confirmed'] is not True:
        raise HTTPException(400,'Confirm Restart or Shut down explicitly.')
    if not available():raise HTTPException(409,'Use the host power controls for this environment.')
    result=await run_in_threadpool(invoke,{'action':'power',**data})
    if not result.get('ok'):raise HTTPException(409,result.get('error','Power action could not be scheduled.'))
    return result
