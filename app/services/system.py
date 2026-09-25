from pathlib import Path
import subprocess


def _model() -> str:
    try:
        return Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
    except Exception:
        return ""


def _uptime() -> str:
    try:
        return subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        ).stdout.strip().removeprefix("up ")
    except Exception:
        return ""


def collect() -> dict:
    return {
        "hostname": Path("/etc/hostname").read_text().strip(),
        "platform": _model(),
        "uptime": _uptime(),
    }
