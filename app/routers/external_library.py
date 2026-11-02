"""Caretaker-authorized fixed-scope external library transition."""
import json
import subprocess
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from starlette.concurrency import run_in_threadpool
from app.routers.https_setup import authenticate
from app.services.library_events import emit

router=APIRouter(prefix='/external-library',tags=['Library storage'])

@router.get('/status')
def status():
    path=Path('/var/lib/dataark/external-library/status.json')
    try:return json.loads(path.read_text())
    except FileNotFoundError:return {'phase':'idle','message':'No external-library transition in progress.'}

def invoke(data):
    try:
        r=subprocess.run(['/usr/bin/sudo','-n','--','/usr/local/libexec/dataark-external-library'],
                         input=json.dumps(data),capture_output=True,text=True,timeout=90)
        value=json.loads(r.stdout)
        if not value.get('ok'):raise ValueError(value.get('error','Storage request failed'))
        return value
    except subprocess.TimeoutExpired:raise ValueError('Drive inspection timed out; check status before retrying.') from None
    except (OSError,json.JSONDecodeError):raise ValueError('External library helper is not installed.') from None

@router.post('/action')
async def action(request:Request):
    await authenticate(request)
    if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'JSON required')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>2048:raise HTTPException(413,'Request too large')
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError('Invalid request')
        value=await run_in_threadpool(invoke,data)
        if data.get('action') in ('copy','switch'):emit('operation_started',action='external_library_'+data['action'])
        return value
    except (ValueError,OSError) as e:raise HTTPException(409,str(e)) from None
