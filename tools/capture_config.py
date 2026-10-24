#!/usr/bin/env python3
"""Capture private appliance configuration; run with sudo on the Pi.

The archive may contain passwords. It stays outside the repository, root-only.
No services or networking settings are changed. This is not a content backup.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import subprocess
import tarfile
import tempfile

CONFIG_PATHS = [
    "/etc/bash.bashrc", "/etc/profile.d/dataark-welcome.sh", "/usr/local/bin/ark-help",
    "/home/admin/.config/dataark-vnc", "/home/admin/.vnc/passwd", "/etc/pam.d/wayvnc", "/usr/local/libexec/dataark-vnc",
    "/etc/dataark-terminal", "/var/lib/shellinabox/known_hosts",
    "/etc/vsftpd.conf", "/etc/ssh", "/etc/docker", "/etc/sudoers", "/etc/sudoers.d",
    "/usr/local/libexec/dataark-library", "/usr/local/libexec/dataark-pass-through",
    "/usr/local/libexec/dataark-portal-monitor", "/etc/default/locale", "/etc/timezone", "/etc/localtime",
    "/boot/firmware/config.txt", "/boot/firmware/cmdline.txt",
    "/home/admin/.ssh/authorized_keys", "/root/.ssh/authorized_keys",
    "/var/lib/samba/private", "/opt/dataark/dataark.yaml", "/opt/dataark/requirements.txt",
    "/etc/dataark", "/etc/sudoers.d/dataark-network", "/usr/local/libexec/dataark-network",
    "/etc/apache2", "/etc/nginx", "/etc/systemd/system",
    "/etc/NetworkManager", "/etc/hostapd", "/etc/dnsmasq.conf",
    "/etc/dnsmasq.d", "/etc/samba", "/etc/network",
    "/etc/dhcpcd.conf", "/etc/nftables.conf", "/etc/iptables",
    "/etc/sysctl.conf", "/etc/sysctl.d", "/etc/fstab",
    "/etc/hosts", "/etc/hostname", "/etc/resolv.conf",
    "/etc/default/kiwix", "/etc/kiwix", "/etc/cron.d",
    "/etc/crontab", "/var/spool/cron/crontabs",
    "/usr/lib/cgi-bin", "/var/www/cgi-bin",
    "/home/admin/kiwix-server/docker-compose.yml",
]
COMMANDS = {
    "os_release": ["cat", "/etc/os-release"],
    "kernel": ["uname", "-a"],
    "python_dependencies": ["/opt/dataark/venv/bin/python", "-m", "pip", "freeze"],
    "repository_revision": ["git", "-c", "safe.directory=/opt/dataark", "-C", "/opt/dataark", "rev-parse", "HEAD"],
    "repository_changes": ["git", "--no-optional-locks", "-c", "safe.directory=/opt/dataark", "-C", "/opt/dataark", "status", "--short"],
    "kiwix_container": ["docker", "inspect", "kiwix-serve"],
    "ssh_effective_settings": ["sshd", "-T"],
    "forwarding": ["sysctl", "net.ipv4.ip_forward", "net.ipv6.conf.all.forwarding"],
    "services": ["systemctl", "list-units", "--all", "--type=service", "--no-pager"],
    "unit_files": ["systemctl", "list-unit-files", "--no-pager"],
    "dataark_unit": ["systemctl", "cat", "dataark.service"],
    "addresses": ["ip", "-j", "address"],
    "routes": ["ip", "-j", "route"],
    "connections": ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show"],
    "mounts": ["findmnt", "--json"],
    "listeners": ["ss", "-lntup"],
    "iptables": ["iptables-save"],
    "nftables": ["nft", "list", "ruleset"],
    "containers": ["docker", "ps", "-a", "--format", "{{.Names}} {{.Image}} {{.Status}} {{.Ports}}"],
    "packages": ["dpkg-query", "-W"],
}

def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo python3 tools/capture_config.py")
    os.umask(0o077)
    parent = Path("/var/backups/dataark")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent.chmod(0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
    output = Path(tempfile.mkdtemp(prefix=stamp, dir=parent))
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "commands": {}, "files": {}, "errors": []}
    for name, command in COMMANDS.items():
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
            report["commands"][name] = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        except (OSError, subprocess.TimeoutExpired) as error:
            report["commands"][name] = {"error": str(error)}
    with tarfile.open(output / "configuration.tar.gz", "w:gz", dereference=False) as archive:
        for name in CONFIG_PATHS:
            path = Path(name)
            if not path.exists() and not path.is_symlink():
                report["files"][name] = "absent"
                continue
            try:
                archive.add(path, arcname=name.lstrip("/"))
                report["files"][name] = "captured"
            except OSError as error:
                report["errors"].append({"path": name, "error": str(error)})
    (output / "inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Private configuration snapshot: {output}")
    print("Contains configuration secrets; do not commit or upload the archive or inventory.")
    print("Content libraries and externally referenced files are not backed up.")
    for name, result in report["commands"].items():
        print(f"{name}: " + ("OK" if result.get("returncode") == 0 else "unavailable (see private inventory)"))
    print(f"Configuration capture errors: {len(report['errors'])}")

if __name__ == "__main__":
    main()
