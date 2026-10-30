from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool
from app.services import software_updates

router=APIRouter(prefix='/software-updates',tags=['Software updates'])

@router.get('')
def current_build():
    """Read the published build identity without contacting the internet."""
    return {'installed':software_updates.installed(),'installation_supported':False}

@router.post('/check')
async def check(preview:bool=False):
    """Check official software releases; no installation or configuration changes."""
    return await run_in_threadpool(software_updates.check,preview)
