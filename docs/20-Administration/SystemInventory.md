# System inventory

Reviewed on the live appliance October 22, 2026. This is an implementation inventory; collection membership and free space change during normal operation.

## Hardware and storage

- Raspberry Pi 4 Model B, with an SD-root filesystem and a separate content SSD mounted at /mnt/storage.
- The content volume is exFAT, labeled OfflineRepo, approximately 954 GiB in filesystem capacity.
- Public orientation files at the SSD root include START-HERE.html, BROWSE.html, README-DATA-ARK.txt and DATA-ARK-CATALOG.json.
- Installed content and pending archives are listed by Manage Library. Do not use a static archive count as an availability check.

## Network and serving

- wlan0: DataArk hotspot, 192.168.4.1/24. wlan1: upstream Wi-Fi client. Ethernet is another possible upstream connection.
- Apache: HTTP port 80, web root /var/www/html, /api proxy to loopback port 8000, /library-files alias to public SSD files.
- FastAPI: dataark.service, user/group admin, checkout /opt/dataark, loopback binding.
- Kiwix: kiwix-serve Docker container, host port 8080, content mount /data from /mnt/storage, configured archive glob *.zim.
- Samba: Offline-Archives is read-only library access; Bugout-Staging is a separate writable upload area; dataark is the development source share. Client guest policy may require Samba authentication.
- vsftpd: anonymous read-only FTP, control port 21 and passive data ports 30000–30009, FTP root containing a read-only library view. No local-account FTP logins or writes.
- OpenSSH: port 22 and configured SFTP subsystem; account-based administrator access. rsync can use SSH; no anonymous rsync daemon is configured.

## Background services

- dataark-update.service and timer: manifest-driven supported Kiwix updates, resume, checksums and activation.
- dataark-maps.service and timer: configured reference-map maintenance.
- dataark-bugout.service: household maintenance and bugout operations.
- dataark-portal-dns.service: dedicated portal DNS behavior alongside the AP's network configuration.
- dataark-pass-through.service: per-device internet-forwarding controls.
- dataark-portal-monitor.service: diagnostic monitor that captures only while Debug is enabled.

## Files and boundaries

- /etc/dataark/network-admin.json contains a salted shared administration-password hash. Its value is private and is not documented here.
- /var/lib/dataark holds worker state and journals; /var/lib/ark holds the common event log and Debug flag.
- /var/log/dataark-portal-monitor contains bounded portal metadata logs.
- /var/backups/dataark and feature-specific backup directories contain private configuration snapshots, not public recovery documentation.
- .dataark-updates, .bugout-staging, upload areas and filesystem metadata are not anonymous FTP content. Library/HTTP and Samba exclusions have their own configuration and must be verified when changed.

Legacy CGI files may exist but are not the active network-management implementation. Do not enable CGI or broaden sudo permissions to make an obsolete script work. See the [architecture](../30-Developer/Architecture.md) and [administrator guide](AdministratorGuide.md).

## Existing remote-access inventory — October 23, 2026

AnyDesk 8.0.4 is installed with an active service. xrdp 0.10.1 and xorgxrdp are installed, xrdp/xrdp-sesman are active and TCP 3389 is listening. OpenSSH server/client/SFTP are installed and TCP 22 is listening. The separate authenticated browser terminal uses HTTPS 4200 and loopback backend 4201. Classic rsh/rlogin/rexec were not found and ports 512–514 were not listening. A subsequent repair installed x11vnc, found the active Wayland session and replaced the obsolete X11 service with native WayVNC. The custom dataark-vnc service is active on private-interface TCP 5901 with encrypted Linux PAM authentication; TLS negotiation and desktop output were checked. The user confirmed Windows RealVNC opened the desktop through both home-LAN and hotspot addresses; keyboard/mouse control, upstream-offline operation and reboot recovery were not separately confirmed. See [VNC](VNC.md). These facts are inventory observations, not successful interactive desktop tests. AnyDesk’s direct/offline operation is not verified. See [Resources beyond the library](../10-User/Resources.md).
