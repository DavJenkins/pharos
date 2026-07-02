from functools import wraps
from pathlib import Path
from datetime import datetime
import json
import time
import traceback

DEBUG_FLAG = Path("/var/lib/ark/debug_status")
LOGFILE = Path("/var/lib/ark/api.log")


def _debug_enabled():
    return DEBUG_FLAG.exists()


def _log(entry):
    try:
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)

        with LOGFILE.open("a") as f:
            json.dump(entry, f)
            f.write("\n")
    except Exception:
        # Logging must never break the API.
        pass


def execute(name):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)

                if _debug_enabled():
                    _log({
                        "time": datetime.now().isoformat(),
                        "operation": name,
                        "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
                        "status": "OK"
                    })

                return result

            except Exception:
                _log({
                    "time": datetime.now().isoformat(),
                    "operation": name,
                    "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
                    "status": "ERROR",
                    "traceback": traceback.format_exc()
                })

                raise

        return wrapper

    return decorator
