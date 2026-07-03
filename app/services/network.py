from pathlib import Path
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
    try:
        return out.split()[2]
    except Exception:
        return ""


def ethernet():
    state = Path("/sys/class/net/eth0/operstate").read_text().strip()

    return {
        "state": state,
        "connected": state == "up",
        "ip": _ip4("eth0"),
        "gateway": _gateway("eth0"),
    }


def wifi():
    link = run(["iw", "dev", "wlan1", "link"])

    if "SSID:" not in link:
        return {
            "state": "disconnected",
            "connected": False,
            "ssid": None,
            "signal": {
                "dbm": None,
                "percent": None,
            },
            "rate": None,
            "ip": "",
            "gateway": "",
        }

    ssid = ""
    dbm = None
    rate = None

    for line in link.splitlines():
        line = line.strip()

        if line.startswith("SSID:"):
            ssid = line.split(":", 1)[1].strip()

        elif line.startswith("signal:"):
            dbm = int(float(line.split()[1]))

        elif line.startswith("tx bitrate:"):
            rate = line.split(":", 1)[1].strip()

    percent = max(0, min(100, int((dbm + 90) * 100 / 60)))

    return {
        "state": "connected",
        "connected": True,
        "ssid": ssid,
        "signal": {
            "dbm": dbm,
            "percent": percent,
        },
        "rate": rate,
        "ip": _ip4("wlan1"),
        "gateway": _gateway("wlan1"),
    }


def access_point():
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
            clients.append({
                "mac": line.split()[1],
            })

    return {
        "ssid": ssid,
        "client_count": len(clients),
        "clients": clients,
    }


def collect():
    return {
        "ethernet": ethernet(),
        "wifi": wifi(),
        "access_point": access_point(),
    }
