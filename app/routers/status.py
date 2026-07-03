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
    return get_status()
