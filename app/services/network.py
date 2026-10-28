from pathlib import Path
from tools.wifi_interfaces import interfaces
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
    carrier = run(["nmcli", "-g", "WIRED-PROPERTIES.CARRIER", "device", "show", "eth0"]).strip()
    autoconnect = run(["nmcli", "-g", "GENERAL.AUTOCONNECT", "device", "show", "eth0"]).strip()
    try:
        state = Path("/sys/class/net/eth0/operstate").read_text().strip()
    except OSError:
        state = "unknown"

    return {
        "carrier": True if carrier == "on" else False if carrier == "off" else None,
        "enabled": True if autoconnect == "yes" else False if autoconnect == "no" else None,
        "state": "disabled" if autoconnect == "no" else state,
        "connected": False if autoconnect == "no" else None if state == "unknown" else state == "up",
        "ip": _ip4("eth0"),
        "gateway": _gateway("eth0"),
    }


def wifi():
    _, upstream = interfaces()
    autoconnect = run(["nmcli", "-g", "GENERAL.AUTOCONNECT", "device", "show", upstream]).strip()
    enabled = True if autoconnect == "yes" else False if autoconnect == "no" else None
    link = run(["iw", "dev", upstream, "link"])

    if "SSID:" not in link:
        return {
            "interface": upstream,
            "enabled": enabled,
            "state": "disabled" if enabled is False else "disconnected" if "Not connected" in link else "unknown",
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
        "interface": upstream,
        "enabled": enabled,
        "state": "connected",
        "connected": True,
        "ssid": ssid,
        "signal": {
            "dbm": dbm,
            "percent": percent,
        },
        "rate": rate,
        "ip": _ip4(upstream),
        "gateway": _gateway(upstream),
    }


def access_point():
    ap, _ = interfaces()
    autoconnect = run(["nmcli", "-g", "GENERAL.AUTOCONNECT", "device", "show", ap]).strip()
    info = run(["iw", "dev", ap, "info"])
    fields = {}
    for line in info.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            fields[parts[0]] = parts[1]
    device_state = run(["nmcli", "-g", "GENERAL.STATE", "device", "show", ap])
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

    stations = run(["iw", "dev", ap, "station", "dump"])

    for line in stations.splitlines():
        if line.startswith("Station "):
            clients.append({
                "mac": line.split()[1],
            })

    return {
        "interface": ap,
        "ssid": ssid,
        "enabled": True if autoconnect == "yes" else False if autoconnect == "no" else None,
        "active": active,
        "state": "unknown" if active is None else "active" if active else "inactive",
        "ip": _ip4(ap),
        "client_count": len(clients),
        "clients": clients,
    }


def collect():
    return {
        "ethernet": ethernet(),
        "wifi": wifi(),
        "access_point": access_point(),
    }
