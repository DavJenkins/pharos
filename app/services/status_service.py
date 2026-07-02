import json
import subprocess
from pathlib import Path

from app.services.network import ethernet, wifi, access_point
from app.services.system import system_info
from app.services.resources import resources

STATUS_FILE = Path("/var/www/html/status.json")


NETWORK_KEYS = {
    "eth_state",
    "eth_ip",
    "eth_gateway",
    "wifi_state",
    "wifi_ssid",
    "wifi_signal_dbm",
    "wifi_signal_pct",
    "wifi_rate",
    "wifi_ip",
    "wifi_gateway",
    "ap_ssid",
    "ap_client_count",
    "ap_clients",
    "hostname",
    "platform",
    "uptime",
    "cpu_temp_c",
    "load_1",
    "load_5",
    "load_15",
    "mem_used",
    "mem_available",
    "swap_used",
    "sd_used",
    "sd_free",
    "sd_pct",
    "ssd_used",
    "ssd_free",
    "ssd_pct",
}


def get_status():
    subprocess.run(
        ["/usr/local/bin/ark-status.sh"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with STATUS_FILE.open() as f:
        status = json.load(f)

    #
    # Remove all Bash-generated network fields.
    #
    for key in NETWORK_KEYS:
        status.pop(key, None)

    #
    # Replace them with native Python values.
    #
    status.update(ethernet())
    status.update(wifi())
    status.update(access_point())
    status.update(system_info())
    status.update(resources())

    return status
