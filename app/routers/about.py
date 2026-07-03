from pathlib import Path
import platform
import subprocess

from fastapi import APIRouter

router = APIRouter(
    prefix="/about",
    tags=["About"],
)


def git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/opt/dataark",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


@router.get("")
def about():

    return {
        "product": "Data Ark",
        "version": "1.0.0",
        "build": git_commit(),
        "hostname": Path("/etc/hostname").read_text().strip(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "api": "v1",
    }
