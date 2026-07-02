import json
import subprocess
from pathlib import Path

from app.services.network import ethernet, wifi

STATUS_FILE = Path("/var/www/html/status.json")


def get_status():
    subprocess.run(
        ["/usr/local/bin/ark-status.sh"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with STATUS_FILE.open() as f:
        status = json.load(f)

    status.update(ethernet())
    status.update(wifi())

    return status
