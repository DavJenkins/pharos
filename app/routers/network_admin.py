import json
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from app.services.network_admin import authorized, invoke

router = APIRouter(prefix='/network/admin', tags=['Network administration'])

@router.post('/{action}')
async def network_action(action: str, request: Request):
    if action not in ('scan', 'connect', 'rename', 'uplink'):
        raise HTTPException(404, 'Unknown network operation')
    header = request.headers.get('authorization', '')
    if len(header) > 2048 or not await run_in_threadpool(authorized, header):
        raise HTTPException(401, 'Enter the network administration password configured on the Pi.')
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise HTTPException(415, 'JSON request required')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4096:
            raise HTTPException(413, 'Request too large')
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(400, 'Invalid JSON') from None
    if not isinstance(data, dict) or 'action' in data:
        raise HTTPException(400, 'Invalid network request')
    result = await run_in_threadpool(invoke, {'action': action, **data})
    if not result['ok']:
        raise HTTPException(400, result.get('error', 'Network operation failed'))
    return result
