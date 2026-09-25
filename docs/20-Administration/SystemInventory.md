# System Inventory

Verified from the Pi diagnostic report and HTTP inspection on 2026-09-24.

- Data Ark API: systemd `dataark.service`, user/group `admin`, bound to loopback port 8000.
- Web server: Apache, port 80; document root `/var/www/html`.
- API proxy: `/api/` forwards to `http://127.0.0.1:8000/`.
- Networking: NetworkManager; `wlan0` uses the `DataArk` profile in AP mode;
  `wlan1` is the upstream Wi-Fi client.
- AP DNS: a dnsmasq process listens on `192.168.4.1:53`; no standalone
  hostapd or dnsmasq unit appeared in the report.
- Kiwix: Docker container `kiwix-serve`, image `ghcr.io/kiwix/kiwix-serve:latest`,
  published on host port 8080. Its root page returned HTTP 200 with the Kiwix title.
- Wi-Fi scripts exist in `/var/www/cgi-bin/`: `get-wifi-list.sh`,
  `save-wifi.sh`, and `save-ap-name.sh`.
- Apache instead maps `/cgi-bin/` to `/usr/lib/cgi-bin/`; no CGI execution
  module appeared in the enabled module list. Do not enable handlers before
  reviewing their authorization, input validation, and privilege use.
- NetworkManager reports `auth` for admin's network-control, profile modification,
  and Wi-Fi scan permissions. An unattended API call cannot assume authorization.

The private configuration snapshot is under `/var/backups/dataark/`; it is not
part of this repository. This inventory contains no configuration passwords.
