from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/debug", tags=["debug"])

DEBUG_FILE = Path("/var/lib/ark/debug_status")


@router.get("")
def get_debug():
    return {
        "debug_mode": DEBUG_FILE.exists()
    }


@router.post("/{state}")
def set_debug(state: str):
    if state.lower() == "on":
        DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEBUG_FILE.touch(exist_ok=True)
    else:
        DEBUG_FILE.unlink(missing_ok=True)

    return {
        "debug_mode": DEBUG_FILE.exists()
    }
