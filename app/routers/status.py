from fastapi import APIRouter

from app.models.status import StatusResponse
from app.services.status_service import get_status

router = APIRouter(
    prefix="/status",
    tags=["Status"],
)


@router.get(
    "",
    response_model=StatusResponse,
    summary="Current appliance status",
)
def status():
    from app.services.integration_health import collect
    result = get_status()
    health = collect(result)
    result['status']['health'] = {key: health[key] for key in ('state', 'problems', 'source_checks')}
    result['status']['issues'] = list(dict.fromkeys(result['status']['issues'] + [p['message'] for p in health['problems']]))
    if health['state'] == 'error':
        result['status']['state'] = 'error'
    elif health['state'] == 'warning' and result['status']['state'] == 'ok':
        result['status']['state'] = 'degraded'
    return result
