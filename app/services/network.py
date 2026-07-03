from app.core.command import run


def _ip4(dev: str) -> str:
    out = run(["ip", "-4", "-o", "addr", "show", "dev", dev])
    if not out:
        return ""

    try:
        return out.split()[3].split("/")[0]
    except Exception:
        return ""


def _gateway(dev: str) -> str:
    out = run(["ip", "route", "show", "default", "dev", dev])
    if not out:
        return ""

    parts = out.split()
    try:
        return parts[2]
    except Exception:
        return ""


def ethernet() -> dict:
    state = run(["cat", "/sys/class/net/eth0/operstate"]) or "down"

    return {
        "state": state,
        "ip": _ip4("eth0"),
        "gateway": _gateway("eth0"),
    }


def wifi() -> dict:
    link = run(["iw", "dev", "wlan1", "link"])

    if "SSID:" not in link:
        return {
            "state": "disconnected",
            "ssid": None,
            "signal": None,
            "rate": None,
            "ip": "",
            "gateway": "",
        }

    ssid = ""
    dbm = None
    rate = ""

    for line in link.splitlines():
        line = line.strip()

        if line.startswith("SSID:"):
            ssid = line.split(":", 1)[1].strip()

        elif line.startswith("signal:"):
            try:
                dbm = int(float(line.split()[1]))
            except Exception:
                pass

        elif line.startswith("tx bitrate:"):
            rate = line.split(":", 1)[1].strip()

    pct = None
    if dbm is not None:
        pct = max(0, min(100, int((dbm + 90) * 100 / 60)))

    return {
        "state": "connected",
        "ssid": ssid,
        "signal": {
            "dbm": dbm,
            "percent": pct,
        },
        "rate": rate,
        "ip": _ip4("wlan1"),
        "gateway": _gateway("wlan1"),
    }


def access_point() -> dict:
    ssid = run([
        "nmcli",
        "-g",
        "802-11-wireless.ssid",
        "connection",
        "show",
        "DataArk",
    ]) or "DataArk"

    clients = []

    stations = run(["iw", "dev", "wlan0", "station", "dump"])

    for line in stations.splitlines():
        if line.startswith("Station "):
            mac = line.split()[1]
            clients.append({
                "mac": mac,
            })

    return {
        "ssid": ssid,
        "clients": clients,
    }


def collect() -> dict:
    return {
        "ethernet": ethernet(),
        "wifi": wifi(),
        "access_point": access_point(),
    }
