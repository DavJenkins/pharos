#!/usr/bin/env python3
"""Read-only diagnostics for Wi-Fi repair and Kiwix health integration.

Does not print passwords, connection profiles, container environments, or keys.
Does not scan Wi-Fi, change connections, or restart services.
"""
from pathlib import Path
import json
import re
import subprocess

def run(label, command, pattern=None):
    print(f"\n--- {label} ---")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        output = result.stdout.strip()
        if pattern:
            output = "\n".join(line for line in output.splitlines() if re.search(pattern, line, re.I))
        print(output or "(no matching output)")
        if result.returncode:
            print(f"Command exit status: {result.returncode}")
    except (OSError, subprocess.TimeoutExpired) as error:
        print(type(error).__name__)

def main():
    run("API service privileges", ["systemctl", "show", "dataark.service", "--property=User,Group,SupplementaryGroups,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateNetwork,RestrictAddressFamilies"])
    run("Relevant services", ["systemctl", "list-units", "--all", "--type=service", "--no-pager", "--plain"], r"dataark|apache|nginx|kiwix|docker|hostapd|dnsmasq|NetworkManager")
    run("Network devices", ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
    run("NetworkManager permissions for admin", ["runuser", "-u", "admin", "--", "nmcli", "general", "permissions"])
    run("AP profile mode and interface", ["nmcli", "-g", "connection.interface-name,802-11-wireless.mode", "connection", "show", "DataArk"])
    run("Containers (no environment or arguments)", ["docker", "ps", "-a", "--format", "{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}"])
    run("TCP listeners", ["ss", "-lntp"])
    run("Apache modules", ["apache2ctl", "-M"], r"cgi|proxy|auth|rewrite|alias")
    print("\n--- Apache route declarations ---")
    for directory in ("/etc/apache2/sites-enabled", "/etc/apache2/conf-enabled"):
        for path in sorted(Path(directory).glob("*")):
            if not path.is_file():
                continue
            for line in path.read_text(errors="replace").splitlines():
                if re.match(r"^\s*(DocumentRoot|ScriptAlias|ProxyPass|ProxyPassReverse|Alias)\s", line, re.I):
                    # Strip any URL userinfo and query strings before display.
                    line = re.sub(r"(https?://)[^/\s]+@", r"\1[redacted]@", line)
                    line = re.sub(r"\?[^\s]+", "?[redacted]", line)
                    print(f"{path.name}: {line.strip()}")
    print("\n--- Existing Wi-Fi CGI files (names only) ---")
    for directory in ("/usr/lib/cgi-bin", "/var/www/cgi-bin", "/var/www/html/cgi-bin", "/opt/dataark"):
        base = Path(directory)
        for name in ("get-wifi-list.sh", "save-wifi.sh", "save-ap-name.sh"):
            for path in base.rglob(name) if base.exists() else []:
                print(path)
    print("\nDone. This report omits configuration secrets; review host and container names before sharing.")

if __name__ == "__main__":
    main()
