"""Public local board and caretaker moderation; no external services."""
import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from app.services import community as board
from app.services.network_admin import authorized

router = APIRouter(prefix='/community',tags=['Community board'])

async def call(function,*args,**kwargs):
    try:return await run_in_threadpool(function,*args,**kwargs)
    except board.BoardError as error:raise HTTPException(error.status,error.message) from None

def peer(request):
    return request.headers.get('x-dataark-peer') or (request.client.host if request.client else 'local')

async def payload(request):
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.headers.get('host'):
        raise HTTPException(403,'Open the board on this Ark before posting.')
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise HTTPException(415,'JSON required')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>24000:raise HTTPException(413,'Message is too large.')
    try:value=json.loads(body)
    except (ValueError,UnicodeError):raise HTTPException(400,'Invalid message') from None
    if not isinstance(value,dict):raise HTTPException(400,'Invalid message')
    return value

async def caretaker(request):
    await call(board.auth_attempt,peer(request))
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):
        raise HTTPException(401,'Caretaker password not accepted.')

@router.get('/threads')
async def listing(category:str='',offset:int=0):
    return await call(board.listing,category,offset)

@router.get('/threads/{identifier}')
async def thread(identifier:int):
    return await call(board.thread,identifier)

@router.post('/threads',status_code=201)
async def create(request:Request):
    return await call(board.create,await payload(request),peer(request))

@router.post('/threads/{identifier}/replies',status_code=201)
async def reply(identifier:int,request:Request):
    return await call(board.create,await payload(request),peer(request),identifier)

@router.post('/messages/{identifier}/remove')
async def remove(identifier:int,request:Request):
    data=await payload(request)
    if data=={'moderator':True}:
        await caretaker(request)
        return await call(board.remove,identifier,moderator=True)
    if set(data)!={'code'}:raise HTTPException(400,'Enter a deletion code or use caretaker moderation.')
    return await call(board.remove,identifier,code=data['code'],peer=peer(request))

def export_backup():
    with tempfile.TemporaryDirectory() as folder:
        file=board.snapshot(Path(folder)/'community.sqlite3')
        return file.read_bytes()

@router.post('/backup')
async def backup(request:Request):
    if await payload(request)!={}:raise HTTPException(400,'Unexpected backup fields.')
    await caretaker(request)
    return Response(await call(export_backup),media_type='application/vnd.sqlite3',headers={
       'Content-Disposition':'attachment; filename="dataark-community.sqlite3"','Cache-Control':'no-store'})

@router.get('/notice')
async def notice():
    return await call(board.notice)

@router.post('/notice')
async def set_notice(request:Request):
    data=await payload(request)
    if set(data) not in ({'text'},{'text','color'}):raise HTTPException(400,'Enter a banner message and optional color.')
    await caretaker(request)
    if 'color' in data:return await call(board.set_notice,data['text'],color=data['color'])
    return await call(board.set_notice,data['text'])
