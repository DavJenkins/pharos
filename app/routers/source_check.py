import json
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from app.services import source_check

router=APIRouter(prefix='/sources/check',tags=['Source availability'])

@router.get('')
def status():return source_check.current()

@router.post('')
async def start(request:Request):
    origin=request.headers.get('origin')
    try:valid=not origin or urlsplit(origin).netloc==request.headers.get('host')
    except ValueError:valid=False
    if not valid:raise HTTPException(403,'Use Check now on this Ark.')
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':raise HTTPException(415,'JSON required')
    body=bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body)>32:raise HTTPException(413,'Request too large')
    try:valid=json.loads(body)=={}
    except ValueError:valid=False
    if not valid:raise HTTPException(400,'No source URLs or options are accepted.')
    try:return await run_in_threadpool(source_check.start)
    except source_check.CheckError as error:raise HTTPException(error.status,error.message) from None
