import subprocess
from pathlib import Path

LEASES = Path("/var/lib/misc/dnsmasq.leases")


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def ethernet():
    state = _run(["cat", "/sys/class/net/eth0/operstate"]) or "down"

    ip = ""
    out = _run(["ip", "-4", "-o", "addr", "show", "dev", "eth0"])
    if out:
        ip = out.split()[3].split("/")[0]

    gw = ""
    out = _run(["ip", "route", "show", "default", "dev", "eth0"])
    if out:
        gw = out.split()[2]

    return {
        "eth_state": state,
        "eth_ip": ip,
        "eth_gateway": gw,
    }


def wifi():
    link = _run(["iw", "dev", "wlan1", "link"])

    state = "disconnected"
    ssid = "Disconnected"
    signal_dbm = ""
    signal_pct = 0
    rate = ""

    if "SSID:" in link:
        state = "connected"

        for line in link.splitlines():
            line = line.strip()

            if line.startswith("SSID:"):
                ssid = line.split(":", 1)[1].strip()

            elif line.startswith("signal:"):
                signal_dbm = line.split()[1]

                try:
                    signal_pct = max(
                        0,
                        min(100, int((float(signal_dbm) + 90) * 100 / 60))
                    )
                except Exception:
                    signal_pct = 0

            elif line.startswith("tx bitrate:"):
                rate = line.split(":", 1)[1].strip()

    ip = ""
    out = _run(["ip", "-4", "-o", "addr", "show", "dev", "wlan1"])
    if out:
        ip = out.split()[3].split("/")[0]

    gw = ""
    out = _run(["ip", "route", "show", "default", "dev", "wlan1"])
    if out:
        gw = out.split()[2]

    return {
        "wifi_state": state,
        "wifi_ssid": ssid,
        "wifi_signal_dbm": signal_dbm,
        "wifi_signal_pct": signal_pct,
        "wifi_rate": rate,
        "wifi_ip": ip,
        "wifi_gateway": gw,
    }


def access_point():
    ap_ssid = (
        _run([
            "nmcli",
            "-g",
            "802-11-wireless.ssid",
            "connection",
            "show",
            "DataArk",
        ])
        or "DataArk"
    )

    leases = {}

    if LEASES.exists():
        for line in LEASES.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                leases[parts[1].lower()] = {
                    "ip": parts[2],
                    "hostname": parts[3] if parts[3] != "*" else "Unknown device",
                }

    clients = []

    stations = _run(["iw", "dev", "wlan0", "station", "dump"])

    for line in stations.splitlines():
        if not line.startswith("Station "):
            continue

        mac = line.split()[1].lower()

        lease = leases.get(mac, {})

        clients.append({
            "hostname": lease.get("hostname", "Unknown device"),
            "ip": lease.get("ip", "No DHCP lease"),
            "mac": mac,
        })

    return {
        "ap_ssid": ap_ssid,
        "ap_client_count": len(clients),
        "ap_clients": clients,
    }
