from pathlib import Path

from fastapi import APIRouter

from app.core.events import info

router = APIRouter(
    prefix="/debug",
    tags=["Debug"],
)

DEBUG_FLAG = Path("/var/lib/ark/debug_status")


@router.get("")
def get_debug():
    return {
        "debug_mode": DEBUG_FLAG.exists()
    }


@router.post("/on")
def debug_on():

    old = DEBUG_FLAG.exists()

    DEBUG_FLAG.touch(exist_ok=True)

    if not old:
        info(
            "debug_mode_changed",
            source="api",
            old=False,
            new=True,
        )

    return {
        "debug_mode": True
    }


@router.post("/off")
def debug_off():

    old = DEBUG_FLAG.exists()

    DEBUG_FLAG.unlink(missing_ok=True)

    if old:
        info(
            "debug_mode_changed",
            source="api",
            old=True,
            new=False,
        )

    return {
        "debug_mode": False
    }
