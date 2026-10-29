from pathlib import Path
from tools.wifi_interfaces import interfaces, ethernet_interface, platform_settings
from tools.wired_interfaces import devices as wired_devices, permanent_mac
import json
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


def ethernet(device=None):
    device=device if device is not None else ethernet_interface()
    if not device:return {'interface':'','carrier':False,'enabled':False,'state':'not_configured','connected':False,'ip':'','gateway':''}
    carrier = run(["nmcli", "-g", "WIRED-PROPERTIES.CARRIER", "device", "show", device]).strip()
    autoconnect = run(["nmcli", "-g", "GENERAL.AUTOCONNECT", "device", "show", device]).strip()
    try:
        state = (Path("/sys/class/net")/device/"operstate").read_text().strip()
    except OSError:
        state = "unknown"

    return {
        "interface": device,
        "permanent_mac": permanent_mac(device),
        "managed": not bool(platform_settings()),
        "carrier": True if carrier == "on" else False if carrier == "off" else None,
        "enabled": True if autoconnect == "yes" else False if autoconnect == "no" else None,
        "state": "disabled" if autoconnect == "no" else state,
        "connected": False if autoconnect == "no" else None if state == "unknown" else state == "up",
        "ip": _ip4(device),
        "gateway": _gateway(device),
    }


def wifi():
    _, upstream = interfaces()
    if not upstream:return {'interface':'','enabled':False,'state':'not_configured','connected':False,'ssid':None,'signal':{'dbm':None,'percent':None},'rate':None,'ip':'','gateway':''}
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
    if not ap:return {'interface':'','ssid':'','enabled':False,'active':False,'state':'not_configured','ip':'','client_count':0,'clients':[]}
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
    names=wired_devices()
    legacy=ethernet_interface()
    if not names and legacy:names=[legacy]
    wired=[ethernet(name) for name in names]
    try:routes=json.loads((run(['ip','-j','route','show','default']) if wired else '') or '[]')
    except (ValueError,TypeError):routes=[]
    for item in wired:
        matching=[r for r in routes if r.get('dev')==item['interface']]
        item['default_route']=bool(matching)
        item['route_metric']=min((r.get('metric',0) for r in matching),default=None)
        raw=run(['ip','-o','addr','show','dev',item['interface']])
        item['addresses']=[line.split()[3] for line in raw.splitlines() if len(line.split())>3 and line.split()[2] in ('inet','inet6')]
    primary=min(wired,key=lambda e:(not bool(e['connected']),e['enabled'] is False,not e['default_route'],e['route_metric'] if e['route_metric'] is not None else 2**32,e['interface'])) if wired else ethernet('')
    return {
        "ethernet": primary,
        "ethernet_interfaces": wired,
        "wifi": wifi(),
        "access_point": access_point(),
    }
