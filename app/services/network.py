import subprocess


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def ethernet():
    state = _run(["cat", "/sys/class/net/eth0/operstate"])
    if not state:
        state = "down"

    ip = ""
    out = _run(["ip", "-4", "-o", "addr", "show", "dev", "eth0"])
    if out:
        ip = out.split()[3].split("/")[0]

    gw = ""
    out = _run(["ip", "route", "show", "default", "dev", "eth0"])
    if out:
        parts = out.split()
        if len(parts) >= 3:
            gw = parts[2]

    return {
        "eth_state": state,
        "eth_ip": ip,
        "eth_gateway": gw,
    }


def wifi():
    link = _run(["iw", "dev", "wlan1", "link"])

    ssid = "Disconnected"
    state = "disconnected"
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
                    pct = (int(float(signal_dbm)) + 90) * 100 / 60
                    signal_pct = max(0, min(100, int(pct)))
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
        parts = out.split()
        if len(parts) >= 3:
            gw = parts[2]

    return {
        "wifi_state": state,
        "wifi_ssid": ssid,
        "wifi_signal_dbm": signal_dbm,
        "wifi_signal_pct": signal_pct,
        "wifi_rate": rate,
        "wifi_ip": ip,
        "wifi_gateway": gw,
    }
