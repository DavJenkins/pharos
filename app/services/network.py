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
    try:
        state = Path("/sys/class/net/eth0/operstate").read_text().strip()
    except OSError:
        state = "unknown"

    return {
        "state": state,
        "connected": None if state == "unknown" else state == "up",
        "ip": _ip4("eth0"),
        "gateway": _gateway("eth0"),
    }


def wifi():
    link = run(["iw", "dev", "wlan1", "link"])

    if "SSID:" not in link:
        return {
            "state": "disconnected" if "Not connected" in link else "unknown",
            "connected": False if "Not connected" in link else None,
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
            try:
                dbm = int(float(line.split()[1]))
            except (ValueError, IndexError):
                dbm = None

        elif line.startswith("tx bitrate:"):
            rate = line.split(":", 1)[1].strip()

    percent = None if dbm is None else max(0, min(100, int((dbm + 90) * 100 / 60)))

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
    info = run(["iw", "dev", "wlan0", "info"])
    fields = {}
    for line in info.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            fields[parts[0]] = parts[1]
    device_state = run(["nmcli", "-g", "GENERAL.STATE", "device", "show", "wlan0"])
    try:
        connected = int(device_state.split()[0]) == 100
    except (ValueError, IndexError):
        connected = None
    if fields.get("type") is None or connected is None:
        active = None
    else:
        active = fields["type"] == "AP" and connected
    ssid = fields.get("ssid") or run([
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
        "active": active,
        "state": "unknown" if active is None else "active" if active else "inactive",
        "ip": _ip4("wlan0"),
        "client_count": len(clients),
        "clients": clients,
    }


def collect():
    return {
        "ethernet": ethernet(),
        "wifi": wifi(),
        "access_point": access_point(),
    }
