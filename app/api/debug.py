from pathlib import Path

from fastapi import APIRouter

from app.core.debugit import execute
from app.core import events

router = APIRouter(prefix="/debug", tags=["debug"])

DEBUG_FILE = Path("/var/lib/ark/debug_status")


@router.get("")
@execute("debug.get")
def get_debug():
    return {
        "debug_mode": DEBUG_FILE.exists()
    }


@router.post("/{state}")
@execute("debug.set")
def set_debug(state: str):

    old = DEBUG_FILE.exists()

    if state.lower() == "on":
        DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEBUG_FILE.touch(exist_ok=True)
    else:
        DEBUG_FILE.unlink(missing_ok=True)

    new = DEBUG_FILE.exists()

    if old != new:
        events.info(
            "debug_mode_changed",
            source="api",
            old=old,
            new=new
        )

    return {
        "debug_mode": new
    }
