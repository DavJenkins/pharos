from datetime import datetime
from pathlib import Path
import subprocess


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def status():
    #
    # System state
    #
    state = "ok"

    root = _run(["df", "-P", "/"]).splitlines()[-1].split()
    sd_pct = int(root[4].rstrip("%"))

    temp = 0.0
    out = _run(["vcgencmd", "measure_temp"])
    if out.startswith("temp="):
        temp = float(out.split("=")[1].split("'")[0])

    if sd_pct >= 90 or temp >= 80:
        state = "critical"
    elif sd_pct >= 80 or temp >= 70:
        state = "warning"

    #
    # Sync status
    #
    sync = "Syncing" if _run(["pgrep", "-x", "rsync"]) else "Idle"

    #
    # Debug mode
    #
    debug = "ON" if Path("/var/lib/ark/debug_status").exists() else "OFF"

    return {
        "system_state": state,
        "sync": sync,
        "debug_mode": debug,
        "updated": datetime.now().strftime("%H:%M:%S"),
    }
