"""Read-only health reporting for Home Assistant and other local clients."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services.integration_health import collect

router = APIRouter(tags=['Health'])

@router.get('/health')
async def health():
    return JSONResponse(await run_in_threadpool(collect), headers={'Cache-Control':'no-store'})
