import platform
import subprocess
from pathlib import Path


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def system_info():
    hostname = platform.node()

    model = ""
    model_file = Path("/proc/device-tree/model")
    if model_file.exists():
        model = model_file.read_text(errors="ignore").replace("\x00", "").strip()

    uptime = _run(["uptime", "-p"])
    if uptime.startswith("up "):
        uptime = uptime[3:]

    return {
        "hostname": hostname,
        "platform": model,
        "uptime": uptime,
    }
