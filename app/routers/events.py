import json
from collections import deque
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

    with EVENT_LOG.open(encoding="utf-8") as stream:
        lines = deque(stream, maxlen=limit)

    records = []
    for line in lines:
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            # A writer may not have finished the last record yet.
            continue
    return records
