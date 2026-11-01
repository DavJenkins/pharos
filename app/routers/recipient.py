"""First-owner setup, gated by a four-digit one-time pairing code supplied with the card."""
import json
import re
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

router=APIRouter(prefix='/recipient',tags=['First-owner setup'])
STATE=Path('/var/lib/dataark/recipient.json')

@router.get('/status')
def status():
    try:state=json.loads(STATE.read_text()).get('state')
    except (OSError,ValueError):state=None
    return {'setup_required':state=='awaiting_local_password'}

def invoke(payload):
    result=subprocess.run(['/usr/bin/sudo','-n','--','/usr/bin/python3','/usr/local/libexec/dataark-recipient','--enroll'],input=json.dumps(payload),capture_output=True,text=True,timeout=15)
    return json.loads(result.stdout)

@router.post('/setup')
async def setup(request:Request):
    origin=request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.headers.get('host'):raise HTTPException(403,'Open setup directly on this Ark.')
    if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'JSON required.')
    body=bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body)>4096:raise HTTPException(413,'Setup request too large.')
    try:
        payload=json.loads(body)
        if not isinstance(payload,dict) or set(payload)!={'code','password','admin_password'} or not all(isinstance(v,str) for v in payload.values()):raise ValueError()
        if not 12<=len(payload['admin_password'])<=256 or not 12<=len(payload['password'])<=256 or not re.fullmatch(r'[0-9]{4}',payload['code']):raise ValueError()
    except (ValueError,TypeError):raise HTTPException(400,'Enter the supplied setup code and a password of 12–256 characters.') from None
    try:result=await run_in_threadpool(invoke,payload)
    except (OSError,ValueError,subprocess.TimeoutExpired):raise HTTPException(503,'Setup is unavailable; try again or use the local terminal.') from None
    if result.get('cooldown'):raise HTTPException(429,'Too many incorrect codes. Wait one minute and try again.',headers={'Retry-After':'60'})
    if not result.get('ok'):raise HTTPException(403,'Setup code not accepted, or setup is already complete.')
    return {'ok':True}
