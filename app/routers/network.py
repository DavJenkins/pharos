from fastapi import APIRouter

from app.services.network import collect

router = APIRouter(
    prefix="/network",
    tags=["Network"],
)


@router.get("")
def network():
    return collect()
