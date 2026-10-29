"""ARM64 software test profile: shared media is deliberately read-only."""
from pathlib import Path
from starlette.responses import JSONResponse
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.base import BaseHTTPMiddleware
from app.main import app as ark_app

# Keep this guard on a separate wrapper; importing tests must not modify the real app.
app = Starlette(routes=[Mount("/", app=ark_app)])

async def protect_test_media(request, call_next):
    if not Path('/etc/dataark-emulator').is_file():
        return JSONResponse({'detail':'The emulator entry point requires an isolated guest marker.'},status_code=503)
    path=request.url.path
    if request.method not in ('GET','HEAD','OPTIONS'):
        allowed=path in ('/library/unlock','/configuration/validate','/debug/on','/debug/off','/support/report') or path.startswith('/community/')
        if not allowed:
            return JSONResponse({'detail':'Read-only emulator: media, network, recovery and household control actions are disabled. Preview configuration or use the physical Ark for these operations.'},status_code=409)
    return await call_next(request)

app.add_middleware(BaseHTTPMiddleware, dispatch=protect_test_media)
