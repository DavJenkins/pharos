from datetime import datetime
from pathlib import Path

from app.services.network import collect as network
from app.services.system import collect as system
from app.services.resources import collect as resources


def get_status():
    return {
        "network": network(),
        "system": system(),
        "resources": resources(),
        "services": {
            "fastapi": "running",
        },
        "status": {
            "state": "ok",
            "debug": Path("/var/lib/ark/debug_status").exists(),
            "sync": "Idle",
            "updated": datetime.now().isoformat(timespec="seconds"),
        },
    }
