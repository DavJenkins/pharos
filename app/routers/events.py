import json
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)

EVENT_LOG = Path("/var/lib/ark/events.log")


@router.get("")
def events(
    limit: int = Query(100, ge=1, le=1000),
):

    if not EVENT_LOG.exists():
        return []

    lines = EVENT_LOG.read_text().splitlines()

    return [
        json.loads(line)
        for line in lines[-limit:]
        if line.strip()
    ]
