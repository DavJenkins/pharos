# AP Welcome Portal

The DataArk access point guides compatible devices to http://192.168.4.1/ and offers optional internet pass-through when the Pi has an upstream connection. Internet forwarding is off by default for AP devices; local content remains accessible.

## Joining the Ark

- Join the DataArk Wi-Fi network and select the device's sign-in notification.
- Explore the local library on the landing page. Use Internet pass-through: Off / On in the upper-right controls to opt this device into internet access; the device may then close its sign-in window.
- Bookmark http://192.168.4.1/ to reopen the library in a full browser. Downloading large archives works best in the full browser.
- Without internet, keep the Wi-Fi connection when the device asks whether to stay connected. Local content remains available.

Opt-ins last up to six hours and reset on reboot or forwarding-service restart. Both the AP device's current IPv4 address and its observed Wi-Fi MAC address must be allowed. A changed address may require opting in again. This is a resource-use control, not user authentication: Wi-Fi MAC/IP addresses can be spoofed. The separate administration password still protects network settings.

The control reports the Ark's upstream availability separately from this device's forwarding permission. Enabling requires a successful upstream probe; disabling remains possible when the upstream is offline. Failure to read the firewall state displays Unavailable rather than falsely claiming Off.

## Install

From /opt/dataark, run the Python tests, deploy the web interface, and restart dataark.service. Then run sudo python3 deploy/install_portal.py. After that installation succeeds, run sudo python3 deploy/install_pass_through.py to enforce default-off forwarding. The latter immediately stops AP internet forwarding until a device opts in. It leaves the Pi's own downloads and local services running. Deploy the updated website and restart dataark.service for the toggle UI/API.

The installer checks the DataArk profile, loopback-only API listener, native dnsmasq/nftables syntax, Apache configuration, a live HTTP probe and the dedicated DNS listener. It backs up affected configuration beneath /var/backups/dataark-portal and rolls back on installation failure. It prints an exact rollback command for later use.

It removes only the exact legacy wlan0 port-80 REDIRECT entries from the live NAT PREROUTING chain and /etc/iptables/rules.v4. It does not save or restore the entire live firewall, flush Docker/NetworkManager rules, restart NetworkManager, reconnect Wi-Fi, or restart Docker. Download jobs can continue.

## How detection works

A separate dnsmasq instance listens on AP port 1053. A private nftables table redirects only IPv4 DNS requests arriving on wlan0 for 192.168.4.1:53. Normal names are forwarded to NetworkManager's existing DNS listener. The Pi's own DNS and upstream interface are unaffected.

Detection hostnames use normal upstream DNS. They must not be overridden with the private AP address: Android can classify that answer as no internet and skip its HTTP probe. Only the local name dataark resolves to 192.168.4.1 through the dedicated listener.

The forwarding table intercepts external IPv4 HTTP on port 80 from AP clients whose MAC and IP are not both opted in. It redirects those connections to a separate Apache listener on port 8081, which sends a non-cacheable 302 to http://192.168.4.1/?portal=1. The listener accepts only AP source addresses. Requests to any of the Pi's local addresses bypass interception, keeping the dashboard and API unchanged. HTTPS is never intercepted. Opted-in clients bypass the redirect and use normal forwarding.

NAT applies when a connection is created. After toggling pass-through, an existing HTTP connection may retain its prior redirect until it closes; retry in a new connection. The forwarding filter still blocks internet traffic immediately when opt-in is removed. Without upstream DNS or cached answers, automatic detection may not run; the local IP remains available offline.

When pass-through is enabled, the API checks the corresponding fixed upstream HTTP probe and returns its real response only when it matches the expected successful result. An offline or unexpected result redirects to the local library. No arbitrary URLs, client cookies or authentication headers are forwarded. Apache overwrites the source-address headers, and the API remains bound to 127.0.0.1:8000.

## Verify on an AP client

- Join from a phone or laptop that has not acknowledged the welcome page. Confirm the sign-in prompt reaches 192.168.4.1 and the local library works.
- With pass-through Off, confirm external HTTP opens the Ark and HTTPS is blocked while local Kiwix works. Turn pass-through On and confirm external browsing works; turn it Off again and verify internet traffic stops. Disable cellular data during this test. Test a second AP device to confirm the first device's opt-in does not enable the second one.
- Confirm local Kiwix, downloads, network administration and Samba still work.
- When convenient, test without an upstream connection: the portal and local content should remain available. Do not disconnect an upstream interface during an active download just to perform this test.
- Reboot later to verify persistence, then repeat the AP-client test.

Automatic sign-in behaviour varies by OS, private DNS, VPN and device policy. Some devices use other probe hosts, HTTPS-only detection, or cellular fallback. These may require manually opening http://192.168.4.1/. The portal cannot force arbitrary HTTPS pages to redirect without certificate errors. Browser connectivity checks use separate HTTPS endpoints and are not overridden by the portal DNS.

## Diagnostics and rollback

Check systemctl status dataark-portal-dns.service --no-pager and journalctl -u dataark-portal-dns.service -n 30 --no-pager. Inspect sudo nft list table ip dataark_portal and sudo iptables -t nat -S PREROUTING.

To disable the welcome DNS immediately, run sudo systemctl disable --now dataark-portal-dns.service. Normal shared DNS remains available; the separate pass-through firewall still controls forwarding and HTTP interception. To restore the complete previous portal configuration, use the installer --rollback command printed at installation. That restores the backed-up configuration files, including the prior saved firewall file; do not use an old backup after unrelated configuration changes without reviewing it.


## Forwarding policy and recovery

The dataark-pass-through.service unit installs its own inet dataark_forward nftables table before NetworkManager starts. It filters forwarded traffic in both directions on wlan0, before the existing NetworkManager/Docker filter chains. Local input/output traffic (including the Pi's downloads, DNS, web server and Samba) is untouched. Published Docker Kiwix traffic on TCP 8080 is explicitly exempted. Other remotely hosted services require pass-through. IPv6 forwarding is blocked; an opt-in currently permits IPv4 forwarding only.

The API invokes a root-owned, fixed-scope helper through a no-arguments sudo rule. The helper validates an AP IPv4 address, obtains the device MAC from the wlan0 neighbor table, and atomically modifies only the two timed allowlists. It does not accept shell commands or arbitrary firewall rules. Apache supplies the real connection address; request bodies cannot choose another device.

The installer validates native nft syntax and sudoers before changes, backs up its files and its own previous table, and prints an explicit rollback command. Reinstalling resets all opt-ins to Off. Stopping the service alone deliberately leaves the filter in place; use the printed rollback command to undo installation. Do not delete firewall tables merely to repair a UI error.

Inspect sudo nft list table inet dataark_forward and systemctl status dataark-pass-through.service --no-pager. If the service fails at boot, its default-off policy may not be installed; inspect and repair it rather than assuming traffic is blocked. No browser-only check proves firewall enforcement: the real AP-device tests above are required after installation.


## Upgrade from DNS-based detection

Run `sudo python3 deploy/install_portal.py` followed by `sudo python3 deploy/install_pass_through.py`. The first installs the dedicated redirect listener and removes detection-host DNS overrides; the second installs HTTP interception and resets opt-ins to Off. Each installer prints its own backup/rollback command and performs native configuration checks before activation. No Wi-Fi, NetworkManager or Docker restart is required. Reconnect the test phone to clear connection state, then verify the sign-in prompt and both pass-through settings. If undoing both steps, roll back pass-through first, then the portal, using the backups from this upgrade.


## Debug-controlled discovery diagnostics

The Settings gear groups Connections, Access and monitoring, and Support tools. All nine icons open a dialog first. Internet access, Auto refresh, and Debug change state only through the button inside their dialog. Desktop hover descriptions remain available. Upstream Wi-Fi and hotspot configuration links appear in their respective dialogs.

The optional `dataark-portal-monitor.service` follows `/var/lib/ark/debug_status`, the existing Debug setting. With Debug off it runs an idle supervisor without tcpdump; with Debug on it captures AP address assignment, ARP, known captive-portal DNS queries, and HTTP connection establishment/reset metadata. It does not record HTTP bodies, passwords, or general DNS names. Logs are local, root-readable, and rotate across four files of approximately 1 MiB each in `/var/log/dataark-portal-monitor/`. The service is limited to 5% of one CPU and 64 MiB of memory; these are limits, not measured typical consumption.

Install with `sudo python3 deploy/install_portal_monitor.py`. Stop permanently with `sudo systemctl disable --now dataark-portal-monitor.service`. Previously captured logs are retained when Debug is off and remain bounded; they are not deleted by toggling Debug.

To investigate a missed Android sign-in prompt, record the approximate failure time, then inspect the rotating logs alongside Apache access/error logs and service status. A fresh forget/rejoin with upstream online was observed to prompt sign-in and open the dashboard. Offline discovery remains a separate unverified test.
