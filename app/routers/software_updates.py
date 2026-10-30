import json
import uuid
from fastapi import APIRouter,HTTPException,Request
from starlette.concurrency import run_in_threadpool
from app.services import software_updates
from app.services import software_installation as installation
from app.services.network_admin import authorized

router=APIRouter(prefix='/software-updates',tags=['Software updates'])

@router.get('')
def current_build():
    """Read the published build identity without contacting the internet."""
    return {'installed':software_updates.installed(),'installation_supported':installation.status().get('installation_supported',False)}

@router.post('/check')
async def check(preview:bool=False):
    """Check official software releases; no installation or configuration changes."""
    return await run_in_threadpool(software_updates.check,preview)

async def caretaker(request):
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):raise HTTPException(401,'Caretaker password required.')

@router.get('/installation')
def installation_status():return installation.status()

@router.post('/stage')
async def stage(request:Request):
    """Verify an explicitly submitted signed package; does not install it."""
    await caretaker(request)
    if request.headers.get('content-type','').split(';')[0] not in ('application/gzip','application/octet-stream'):raise HTTPException(415,'Upload a signed .tar.gz software package.')
    identifier=uuid.uuid4().hex;path=installation.INBOX/(identifier+'.tar.gz');size=0
    try:
        with path.open('xb') as stream:
            async for chunk in request.stream():
                size+=len(chunk)
                if size>256*1024*1024:raise HTTPException(413,'Software package exceeds 256 MiB.')
                stream.write(chunk)
        if not size:raise HTTPException(400,'Software package is empty.')
        result=await run_in_threadpool(installation.invoke,{'action':'stage','id':identifier})
        if not result.get('ok'):raise HTTPException(400,result.get('error','Package verification failed.'))
        return result
    except OSError:raise HTTPException(503,'Software staging storage is unavailable.') from None
    finally:path.unlink(missing_ok=True)

@router.post('/install')
async def install(request:Request):
    await caretaker(request)
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>1024:raise HTTPException(413,'Request too large.')
    try:
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!={'id'}:raise ValueError()
    except (ValueError,UnicodeError):raise HTTPException(400,'Supply the verified staged package ID.') from None
    result=await run_in_threadpool(installation.invoke,{'action':'apply','id':value['id']})
    if not result.get('ok'):raise HTTPException(400,result.get('error','Update could not start.'))
    return result
