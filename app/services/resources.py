from pathlib import Path
import subprocess


def _run(cmd):
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except Exception:
        return ""


def _human(n: int) -> str:
    units = ["B","KiB","MiB","GiB","TiB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}"
        f /= 1024


def _meminfo():
    d = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        d[k] = int(v.split()[0]) * 1024
    return d


def _df(path):
    out = _run(["df", "-B1", path]).splitlines()
    if len(out) < 2:
        return {"used":"","free":"","percent":0}
    f = out[1].split()
    return {
        "used": _human(int(f[2])),
        "free": _human(int(f[3])),
        "percent": int(f[4].rstrip("%")),
    }


def _cpu_temp():
    out = _run(["vcgencmd","measure_temp"])
    try:
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return 0.0


def collect():
    mem = _meminfo()

    with open("/proc/loadavg") as f:
        load = f.read().split()[:3]

    return {
        "cpu": {
            "temperature_c": _cpu_temp(),
            "load": [float(x) for x in load],
        },
        "memory": {
            "used": _human(mem["MemTotal"] - mem["MemAvailable"]),
            "available": _human(mem["MemAvailable"]),
            "swap_used": _human(mem["SwapTotal"] - mem["SwapFree"]),
        },
        "storage": {
            "sd": _df("/"),
            "ssd": _df("/mnt/storage"),
        },
    }
