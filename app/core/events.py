from datetime import datetime
from pathlib import Path
import json

LOGFILE = Path("/var/lib/ark/events.log")


def _write(level, event, source="unknown", **fields):
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "source": source,
        "event": event,
    }

    entry.update(fields)

    with LOGFILE.open("a") as f:
        json.dump(entry, f)
        f.write("\n")


def info(event, source="unknown", **fields):
    _write("INFO", event, source, **fields)


def warning(event, source="unknown", **fields):
    _write("WARNING", event, source, **fields)


def error(event, source="unknown", **fields):
    _write("ERROR", event, source, **fields)
