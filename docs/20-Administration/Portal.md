# AP Welcome Portal

The DataArk access point guides compatible devices to http://192.168.4.1/ while retaining normal internet forwarding whenever the Pi has an upstream connection. This is an introduction to the library, not a login system or an access-control firewall.

## Joining the Ark

- Join the DataArk Wi-Fi network and select the device's sign-in notification.
- Explore the local library on the landing page. Select Continue with internet access when ready; the device may then close its sign-in window.
- Bookmark http://192.168.4.1/ to reopen the library in a full browser. Downloading large archives works best in the full browser.
- Without internet, keep the Wi-Fi connection when the device asks whether to stay connected. Local content remains available.

The welcome acknowledgement lasts six hours per AP IPv4 address and resets on API restart. It does not identify a person or authenticate a device. A device reusing an acknowledged DHCP address can inherit that acknowledgement. The Ark does not prevent browsing before acknowledgement.

## Install

From /opt/dataark, run the Python tests, deploy the web interface, and restart dataark.service. Then run sudo python3 deploy/install_portal.py.

The installer checks the DataArk profile, loopback-only API listener, native dnsmasq/nftables syntax, Apache configuration, a live HTTP probe and the dedicated DNS listener. It backs up affected configuration beneath /var/backups/dataark-portal and rolls back on installation failure. It prints an exact rollback command for later use.

It removes only the exact legacy wlan0 port-80 REDIRECT entries from the live NAT PREROUTING chain and /etc/iptables/rules.v4. It does not save or restore the entire live firewall, flush Docker/NetworkManager rules, restart NetworkManager, reconnect Wi-Fi, or restart Docker. Download jobs can continue.

## How detection works

A separate dnsmasq instance listens on AP port 1053. A private nftables table redirects only IPv4 DNS requests arriving on wlan0 for 192.168.4.1:53. Normal names are forwarded to NetworkManager's existing DNS listener. The Pi's own DNS and upstream interface are unaffected.

Only these dedicated detection hostnames resolve to the portal: connectivitycheck.gstatic.com, connectivitycheck.android.com, captive.apple.com, www.msftconnecttest.com and www.msftncsi.com. Apache routes their known HTTP probe paths to the API, which redirects AP clients to the canonical landing address. Ordinary websites and HTTPS are not intercepted.

After acknowledgement, the API checks the corresponding fixed upstream HTTP probe and returns its real response only when it matches the expected successful result. An offline or unexpected result redirects to the local library. No arbitrary URLs, client cookies or authentication headers are forwarded. Apache overwrites the source-address headers, and the API remains bound to 127.0.0.1:8000.

## Verify on an AP client

- Join from a phone or laptop that has not acknowledged the welcome page. Confirm the sign-in prompt reaches 192.168.4.1 and the local library works.
- Choose Continue with internet access. With upstream internet available, confirm both an ordinary HTTP site and an HTTPS site work in the normal browser. Confirm the Ark's online links become available.
- Confirm local Kiwix, downloads, network administration and Samba still work.
- When convenient, test without an upstream connection: the portal and local content should remain available. Do not disconnect an upstream interface during an active download just to perform this test.
- Reboot later to verify persistence, then repeat the AP-client test.

Automatic sign-in behaviour varies by OS, private DNS, VPN and device policy. Some devices use other probe hosts, HTTPS-only detection, or cellular fallback. These may require manually opening http://192.168.4.1/. The portal cannot force arbitrary HTTPS pages to redirect without certificate errors. Browser connectivity checks use separate HTTPS endpoints and are not overridden by the portal DNS.

## Diagnostics and rollback

Check systemctl status dataark-portal-dns.service --no-pager and journalctl -u dataark-portal-dns.service -n 30 --no-pager. Inspect sudo nft list table ip dataark_portal and sudo iptables -t nat -S PREROUTING.

To disable the welcome DNS immediately, run sudo systemctl disable --now dataark-portal-dns.service. Normal shared DNS and internet forwarding remain available. To restore the complete previous portal configuration, use the installer --rollback command printed at installation. That restores the backed-up configuration files, including the prior saved firewall file; do not use an old backup after unrelated configuration changes without reviewing it.
