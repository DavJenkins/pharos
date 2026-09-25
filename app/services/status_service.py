from datetime import datetime, timezone
from pathlib import Path

from app.services.update_status import progress
from app.services.network import collect as network
from app.services.system import collect as system
from app.services.resources import collect as resources
from app.services.health import assess, services, sync_state


def get_status():
    sections = {}
    unavailable = []
    for name, collect in (("network", network), ("system", system), ("resources", resources)):
        try:
            sections[name] = collect()
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            sections[name] = None
            unavailable.append(f"{name.capitalize()} telemetry unavailable")
    service_states = services()
    sync = sync_state()
    state, issues = assess(sections["resources"], service_states, sync, unavailable)
    return {
        **sections,
        "services": service_states,
        "status": {
            "state": state,
            "issues": issues,
            "debug": Path("/var/lib/ark/debug_status").exists(),
            "sync": sync,
            "update": progress(),
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
