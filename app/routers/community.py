"""Public local board and caretaker moderation; no external services."""
import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from app.services import community as board
from app.services import community_restore as restore
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
    if 'text' not in data or set(data)-{'text','color','text_color','width','margin','margin_top','margin_bottom'}:raise HTTPException(400,'Enter a banner message and supported appearance settings.')
    await caretaker(request)
    return await call(board.set_notice,data['text'],**{key:value for key,value in data.items() if key!='text'})


@router.post('/restore/preview')
async def restore_preview(request:Request):
    origin=request.headers.get('origin')
    try:valid=not origin or urlsplit(origin).netloc==request.headers.get('host')
    except ValueError:valid=False
    if not valid:raise HTTPException(403,'Use Restore on this Ark.')
    if request.headers.get('content-type','').split(';')[0].lower() not in ('application/vnd.sqlite3','application/octet-stream'):
        raise HTTPException(415,'Choose a SQLite board backup.')
    await caretaker(request)
    try:length=int(request.headers.get('content-length','0'))
    except ValueError:raise HTTPException(400,'Invalid upload length') from None
    if length>restore.MAX_UPLOAD:raise HTTPException(413,'Backup exceeds 128 MiB.')
    target=None
    try:
        with tempfile.NamedTemporaryFile(dir=board.DATABASE.parent,prefix='.restore-upload-',delete=False) as stream:
            target=Path(stream.name);size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>restore.MAX_UPLOAD:raise HTTPException(413,'Backup exceeds 128 MiB.')
                await run_in_threadpool(stream.write,chunk)
        return await call(restore.prepare,target,peer(request))
    except OSError:raise HTTPException(503,'Unable to stage the backup. Check the Pi’s private storage.') from None
    finally:
        if target is not None:
            try:target.unlink(missing_ok=True)
            except OSError:pass

@router.post('/restore/apply')
async def restore_apply(request:Request):
    data=await payload(request)
    if set(data)!={'token','confirmation'} or data['confirmation']!='RESTORE':
        raise HTTPException(400,'Validate a backup and explicitly confirm replacement first.')
    await caretaker(request)
    return await call(restore.apply,data['token'],peer(request))
