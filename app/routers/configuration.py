import json
from fastapi import APIRouter,HTTPException,Request
from starlette.concurrency import run_in_threadpool
from app.services import configuration as service
from app.services.network_admin import authorized,invoke

router=APIRouter(prefix='/configuration',tags=['Configuration'])

async def authorize(request):
    if not await run_in_threadpool(authorized,request.headers.get('authorization','')[:2049]):raise HTTPException(401,'Caretaker password required.')

@router.get('/status')
def status():
    value=service.status()
    if value.get('state')=='error':value={**value,'message':'Configuration was not applied. Load configuration for details.'}
    return value

@router.get('')
async def read(request:Request,file:str|None=None):
    try:return await run_in_threadpool(service.read,file) if file is not None else await run_in_threadpool(service.read)
    except ValueError as error:raise HTTPException(400,str(error)) from None

@router.get('/history/{identifier}')
async def history(identifier:str,request:Request):
    try:return await run_in_threadpool(service.history,identifier)
    except (ValueError,OSError):raise HTTPException(404,'Saved configuration not found.') from None

@router.post('/{action}')
async def change(action:str,request:Request):
    if action not in ('validate','save','community'):raise HTTPException(404,'Unknown configuration operation.')
    if action!='validate':await authorize(request)
    if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'JSON required.')
    body=bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body)>8*1024*1024:raise HTTPException(413,'Configuration request exceeds 8 MiB.')
    try:
        data=json.loads(body)
        if not isinstance(data,dict):raise ValueError('Expected a configuration request.')
        if action=='community':
            if set(data)!={'enabled','revision'} or type(data['enabled']) is not bool:raise ValueError('Community visibility must be on or off.')
            _,live=await run_in_threadpool(service.current)
            public=service.public(live);public['community']={'enabled':data['enabled']};text=service.dump(public)
        else:
            if set(data)-{'text','revision','file'}:raise ValueError('Unsupported configuration field.')
            text=data.get('text')
        file=data.get('file') if action!='community' else None
        if file is not None and not isinstance(file,str):raise ValueError('Invalid configuration file.')
        if action=='validate':return await run_in_threadpool(service.preview,text,file) if file is not None else await run_in_threadpool(service.preview,text)
        result=await run_in_threadpool(service.queue,text,data.get('revision'),file) if file is not None else await run_in_threadpool(service.queue,text,data.get('revision'))
        started=await run_in_threadpool(invoke,{'action':'publish-configuration'})
        if not started.get('ok'):
            service.write_json(service.STATE/'status.json',{'state':'error','message':'Publisher could not start. No configuration was applied.'})
            raise ValueError('Publisher could not start. No configuration was applied.')
        return result
    except (ValueError,OSError,RecursionError) as error:raise HTTPException(400,str(error)) from None
