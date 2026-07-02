import json
import subprocess
from pathlib import Path

STATUS_FILE = Path("/var/www/html/status.json")


def get_status():
    try:
        subprocess.run(
            ["/usr/local/bin/ark-status.sh"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with STATUS_FILE.open("r") as f:
            return json.load(f)

    except Exception as ex:
        return {
            "system_state": "error",
            "error": str(ex),
        }
