import subprocess


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def _bytes_human(n):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    n = float(n)
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.1f} {units[i]}"


def resources():
    load1, load5, load15 = open("/proc/loadavg").read().split()[:3]

    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0]) * 1024

    mem_used = mem["MemTotal"] - mem["MemAvailable"]
    swap_used = mem["SwapTotal"] - mem["SwapFree"]

    root = _run(["df", "-B1", "/"]).splitlines()[-1].split()
    sd_used = int(root[2])
    sd_free = int(root[3])
    sd_pct = int(root[4].rstrip("%"))

    ssd_used = ssd_free = ssd_pct = 0
    ssd = _run(["df", "-B1", "/mnt/storage"])
    if ssd:
        parts = ssd.splitlines()[-1].split()
        if len(parts) >= 5:
            ssd_used = int(parts[2])
            ssd_free = int(parts[3])
            ssd_pct = int(parts[4].rstrip("%"))

    temp = 0.0
    out = _run(["vcgencmd", "measure_temp"])
    if out.startswith("temp="):
        temp = float(out.split("=")[1].split("'")[0])

    return {
        "cpu_temp_c": temp,
        "load_1": load1,
        "load_5": load5,
        "load_15": load15,
        "mem_used": _bytes_human(mem_used),
        "mem_available": _bytes_human(mem["MemAvailable"]),
        "swap_used": _bytes_human(swap_used),
        "sd_used": _bytes_human(sd_used),
        "sd_free": _bytes_human(sd_free),
        "sd_pct": sd_pct,
        "ssd_used": _bytes_human(ssd_used),
        "ssd_free": _bytes_human(ssd_free),
        "ssd_pct": ssd_pct,
    }
