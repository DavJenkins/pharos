from pathlib import Path

from app.services.network import collect as network
from app.services.system import collect as system
from app.services.resources import collect as resources


def get_status():

    debug = Path("/var/lib/ark/debug_status").exists()

    return {
        "network": network(),
        "system": system(),
        "resources": resources(),
        "status": {
            "state": "ok",
            "debug": debug,
        },
    }
