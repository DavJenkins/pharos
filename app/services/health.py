"""Bounded probes for the services documented by this appliance."""
import subprocess
from http.client import HTTPConnection, HTTPException

from tools.wifi_interfaces import platform_settings

UNITS = {"apache": "apache2.service", "network_manager": "NetworkManager.service", "samba": "smbd.service"}

def sync_state():
    from app.services.update_status import progress
    current = progress()
    if current is not None:
        return current["label"]
    # This is rsync process activity, not verification of archive freshness.
    try:
        result = subprocess.run(["pgrep", "-x", "rsync"], capture_output=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "Unavailable"
    return {0: "Syncing", 1: "Idle"}.get(result.returncode, "Unavailable")

def kiwix_state():
    # Probe the published loopback port; Docker socket access is unnecessary.
    connection = HTTPConnection("127.0.0.1", 8080, timeout=2)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        if response.status != 200:
            return "unhealthy"
        # Bound the read and distinguish the verified Kiwix page from a generic 200.
        page = response.read(4096)
        return "running" if b"<title>Welcome to Kiwix Server</title>" in page else "unhealthy"
    except (OSError, HTTPException):
        return "unavailable"
    finally:
        connection.close()


def services():
    units={name:unit for name,unit in UNITS.items() if name!="network_manager" or not platform_settings()}
    states = {"fastapi": "running", "kiwix": kiwix_state(), **{name: "unknown" for name in units}}
    if "network_manager" not in units:states["network_manager"]="not_applicable"
    try:
        result = subprocess.run(
            ["systemctl", "show", *units.values(), "--property=Id,LoadState,ActiveState", "--no-pager"],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return states
    for block in result.stdout.strip().split("\n\n"):
        values = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        for name, unit in units.items():
            if values.get("Id") == unit:
                if values.get("LoadState") == "not-found":
                    states[name] = "not_installed"
                else:
                    state = values.get("ActiveState", "unknown")
                    states[name] = "running" if state == "active" else state
    return states

def assess(resources, service_states, sync, unavailable):
    issues = list(unavailable)
    critical = False
    settings=platform_settings()
    if settings.get("configuration_error"):issues.append("Platform configuration is invalid")
    if resources is not None:
        temperature = resources["cpu"]["temperature_c"]
        if temperature is None:
            if not settings:issues.append("CPU temperature unavailable")
        elif temperature >= 70:
            issues.append("CPU temperature is high")
            critical |= temperature >= 80
        for name, disk in resources["storage"].items():
            percent = disk["percent"]
            if percent is None:
                issues.append(f"{name.upper()} storage unavailable")
            elif percent >= 80:
                issues.append(f"{name.upper()} storage usage is high")
                critical |= percent >= 90
    for name, state in service_states.items():
        if state not in ("running","not_applicable"):
            issues.append(f"{name}: {state}")
    if sync.startswith(("Update failed", "Update status")):
        issues.append(sync)
    if sync == "Unavailable":
        issues.append("Sync activity unavailable")
    return ("error" if critical else "degraded" if issues else "ok"), issues
