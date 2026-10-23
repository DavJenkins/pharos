# Configuration reference

## How to read this reference

This records the settings observed on the deployed Ark on October 22, 2026, and points to reproducible source where it exists. Installed helper copies are not automatically updated by editing the repository. Site-specific secrets belong in the root-only configuration capture, not this page.

Do not paste all commands into a running appliance. Network, mount and firewall changes can sever access or interrupt real work. For a new build, use spare media and a local recovery console until the bootstrap process has been validated.

## Base system and prerequisites

- Observed platform: Raspberry Pi 4 Model B, aarch64, Debian 13 trixie, Python 3.13.5.
- Repository: /opt/dataark; Python environment: /opt/dataark/venv; dependency pins: requirements.txt.
- Required components include Apache with proxy/proxy_http/headers/autoindex, OpenSSH, Samba, NetworkManager, Docker, dnsmasq, nftables, curl, rsync, tcpdump and vsftpd for the corresponding features. Map and household workers have additional dependencies checked by their installers.
- Keep /etc/hostname, /etc/hosts, timezone, time synchronization and wireless regulatory country consistent with the installation. Do not use this host's disk or network identity on another appliance without review.
- Keep a local console or alternate route before changing the AP, upstream connection or forwarding rules.

The private snapshot records the installed package list and Python freeze. A clean-image dependency recipe and fixed container digest still need validation; the running Kiwix deployment uses a latest image reference, which is not an immutable software version.

## Observed hardware and boot settings

The reviewed storage device identifies as MZVLB1T0HALR (about 954 GiB), behind a JMicron USB storage bridge; the SD capacity is about 116.5 GiB. A Netgear A6150/Realtek RTL8812BU USB Wi-Fi adapter supplies the additional radio. Multiple USB hubs are present. The storage bridge appeared in the USB 2.0 bus tree during this review; do not assume the USB 3-capable bridge is actually using a SuperSpeed path. Port placement, hub power and actual I/O performance need verification, especially when readers stall during writes.

The Pi reports roughly 1.8 GiB usable RAM with zram swap present. Power-supply rating, enclosure cooling, optional RTC/UPS hardware and spare-media restore results are not established by this inventory. Record them after physical inspection instead of inventing a hardware bill of materials.

Observed boot configuration includes arm_64bit=1, auto_initramfs=1, vc4-kms-v3d, arm_boost=1, audio/camera/display auto-detection and display defaults. Conditional cm4/cm5 entries are image defaults, not Pi 4 requirements. The observed config is saved as a review reference, not a portable prescription for all boards.

Hostname is dataark; timezone is America/New_York and NTP was synchronized at review. An offline appliance still needs a clock strategy; previous online synchronization does not establish accurate time after every powerless boot. Both 99-ip-forward.conf and 99-ipforward.conf exist under /etc/sysctl.d; inspect effective settings and duplicates before consolidating them.

## Filesystem and ownership

The content SSD is mounted at /mnt/storage as exFAT, volume label OfflineRepo. The observed fstab entry uses content UUID 22CB-1D5C and options defaults,uid=1000,gid=1000,umask=000 with dump/fsck fields 0 0. This UUID is specific to this drive. On another disk, discover its UUID and verify the intended device; do not reuse it or format a disk automatically.

The reviewed admin account maps to UID/GID 1000. exFAT presents permissions from its mount options rather than ordinary per-file Unix ownership semantics. Public read-only access therefore depends on service configuration and, for FTP, a read-only mount namespace. A writable local SSD does not imply anonymous users may write to it.

The SD root uses ext4 with noatime, and /boot/firmware uses vfat. Their PARTUUID values are installation-specific. Boot firmware config and kernel command-line settings are captured privately for comparison; do not copy SD partition identifiers to new media.

## NetworkManager hotspot and upstream

The DataArk profile is AP mode on wlan0, autoconnect enabled, ipv4.method shared, address 192.168.4.1/24. NetworkManager provides the base shared-network/DHCP behavior. wlan1 is the separate upstream client. AP and upstream credentials are site-specific and must be entered or restored privately.

Keep the AP subnet distinct from the upstream network. The interface names are part of today's deployment, not a portable hardware guarantee. A bootstrap must verify AP capability and select the correct physical interfaces before writing profiles. The kernel's observed net.ipv4.ip_forward setting is 1.

The hostname dataark is useful where local resolution works. The portal explicitly supplies a local dataark answer on the hotspot, but clients can have different search/mDNS policies. The fixed hotspot address remains the manual fallback.

## Apache and API

- Apache listens on port 80 and serves /var/www/html.
- The port-80 virtual host has ProxyPreserveHost On, ProxyPass /api/ to http://127.0.0.1:8000/ and the corresponding ProxyPassReverse.
- The current main document-root directory permits Indexes FollowSymLinks, AllowOverride All and Require all granted. These are observed settings, not a reason to enable executable handling for content.
- /etc/apache2/conf-enabled/dataark-content.conf aliases /library-files/ to /mnt/storage. That directory has Indexes, AllowOverride None, Require all granted, default-handler, disabled DirectoryIndex, binary MIME types for archives/programs and separate exclusions for hidden/private/staging paths. FollowSymLinks is not enabled on this content alias.
- /etc/apache2/conf-enabled/dataark-portal.conf supplies trusted peer-header handling and portal interception/listeners described below.
- API unit /etc/systemd/system/dataark.service runs as admin:admin, working directory /opt/dataark, using venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000. Restart is always with a five-second delay.

The observed service and virtual-host templates are tracked under deploy/reference for reconstruction review. They are not installed automatically. Editing Python requires API restart; publishing static files does not restart the API.

The web deployment script renders the dashboard, builds docs in a fresh temporary directory, and rsyncs static output. Documentation deployment explicitly uses --chmod=D755,F644; missing search permissions previously caused Help to return access errors. Help links directly to /docs/SUMMARY.html.

## Captive portal and pass-through

The portal installer writes /etc/dataark/portal-dns.conf, portal.nft, Apache portal configuration and dataark-portal-dns.service. Dedicated dnsmasq listens on 1053 on the AP, forwards ordinary questions to 192.168.4.1:53, has a cache of 150 and local TTL 30, and supplies dataark at 192.168.4.1. It deliberately does not replace known OS discovery hosts with private addresses indiscriminately.

The ip dataark_portal table redirects AP-to-Ark TCP/UDP DNS requests from 53 to 1053. The service validates dnsmasq configuration, installs its owned table, and removes that table on stop. Do not flush the entire nftables ruleset: Docker and NetworkManager have separate requirements.

The pass-through installer owns inet dataark_forward. Timed MAC and IPv4 sets expire after six hours. Unapproved AP clients' nonlocal HTTP is directed to the separate 8081 welcome listener; local Pi addresses remain local. Forwarding rules preserve the Docker-DNAT Kiwix path and reject unauthorized AP forwarding, including IPv6. An approved client is checked against the per-device allowlists; permission is not a global switch and does not persist across reboot.

Apache overwrites X-DataArk-Peer from the connection peer and removes client-supplied server identity. Port 8081 only accepts AP-subnet callers and redirects to http://192.168.4.1/?portal=1. Portal mutation requires the expected local Origin and verified AP peer. Direct access to the backend would undermine those assumptions; keep it loopback-only.

Installers: deploy/install_portal.py and deploy/install_pass_through.py. Verify discovery and manual access from a real client and test offline separately; a running DNS daemon does not establish that all phone pop-ups behave identically.

## Kiwix container

The existing compose source is /home/admin/kiwix-server/docker-compose.yml. The container name is kiwix-serve, published on host port 8080, restart policy unless-stopped, startup command glob *.zim and /mnt/storage mounted at /data. The observed bind is read-write; do not describe the container mount as read-only without changing and testing it. The activation tool checks the reviewed entrypoint, command and content mount before switching archives.

The collection catalogue and article-serving path need separate checks. Startup after a restart can take time to read archives. A Docker process in running state, HTTP homepage or catalogue is not sufficient evidence that article/image requests work.

## Content updater and manifest

dataark.yaml controls repository visibility, registered asset paths, source series, hashes, update policy, map coverage, resource indexes and household job configuration. hide_missing is true. Removed files retain records marked removed with manual/never updates; reinstatement re-enables a supported source. Source details and published runtime state can differ from the last Git commit, so capture the live manifest too.

dataark-update.timer uses OnBootSec=2min, OnUnitInactiveSec=5min and AccuracySec=30s. Per-asset refresh intervals decide which publisher checks are due. Its root oneshot has ConditionPathIsMountPoint=/mnt/storage, Nice=10, idle I/O scheduling, unlimited start duration, 45-second stop allowance and control-group termination.

Worker state is /var/lib/dataark/updates; downloads and transaction files are in /mnt/storage/.dataark-updates. Locks, publisher size/hash checks, snapshot-change detection, reader catalogue checks and rollback journals are required parts of the lifecycle. Do not delete them to clear a failed status. Deploy/install_update_worker.py creates the unit/timer.

## Library/network administration authentication

/etc/dataark/network-admin.json contains a salted PBKDF2-SHA256 hash, not the original shared password. The current implementation uses 300000 iterations. The directory is root:admin 0750 and the credential file root:admin 0640 so the API account can verify it. Do not publish its contents.

Root-owned helpers live under /usr/local/libexec. Reviewed sudoers files allow the network, library and pass-through helpers with no command-line arguments. Library operations accept only fixed operations and registered identifiers; callers do not supply shell commands or arbitrary deletion/download paths.

Deploy/install_network_admin.py preserves the existing credential unless explicitly reset. Deploy/install_library.py updates its installed helper but does not initiate a collection download. The library UI remembers successful authentication in page memory, expires after 15 minutes since successful activity, and clears on navigation, reload, explicit lock or 401. Removal still requires confirmation.

This application uses local HTTP, not encrypted management transport. The caretaker password is not an SSH or Samba account. Keep credential use within the intended local deployment boundary and document any future transport/authentication changes.

## Samba

/etc/samba/smb.conf defines Offline-Archives at /mnt/storage, read-only, with guest access offered subject to client policy. Bugout-Staging is a separate writable area at /mnt/storage/bugout-drop. The dataark development share points to /opt/dataark and is writable according to its account policy. Do not change the development share into an anonymous public source server merely to provide source references.

Deploy/install_content_access.py validates candidates with testparm and Apache configtest, preserves configuration backups and maintains public content exclusions. SMB account state is separate from configuration text; the private capture includes Samba private state so a maintainer can review recovery needs. Do not copy that state into the public library.

## Anonymous FTP

Tracked configuration: deploy/ftp/vsftpd.conf and deploy/ftp/dataark.conf. Install the Debian vsftpd package, then use deploy/install_ftp.py. The installer backs up existing configuration, installs a systemd drop-in and enables/restarts the server.

Anonymous login is allowed without a password; local account FTP login and all writes are disabled. FTP control is port 21, passive data ports are 30000–30009, active mode is disabled, max clients is 12 and max connections per IP is 4. Idle timeout is 300 seconds and connection/accept timeouts are 60 seconds. Only world-readable files can be downloaded anonymously.

anon_root is /srv/dataark-ftp. The service privately binds /mnt/storage read-only at /srv/dataark-ftp/library, requires the SSD mount, protects home/system paths and masks private/staging/system-metadata directories. hide_file and deny_file provide additional exclusions. Clients enter /library. File additions/removals appear through the live directory bind; individual archives must not be pinned with per-file bind mounts that retain deleted storage.

The exact drop-in masks .dataark-updates, .bugout-staging, bugout-drop, System Volume Information and $RECYCLE.BIN. Verify anonymous listing, small download, resume, rejected writes and denied directory entry after changes. Logs are normal vsftpd transfer/service logs, not the library management event stream.

## SSH, SFTP and rsync

Observed SSH policy: public-key authentication enabled, password authentication enabled, root login without-password, and the SFTP subsystem at /usr/lib/openssh/sftp-server. Preserve the intended account/key policy rather than resetting it to match a convenience password. SSH listens on 22. SFTP and rsync over SSH use that account's permissions. No anonymous rsync daemon or WebDAV server is configured.

SSH host keys, authorized keys and account private keys have distinct roles. The private configuration capture includes host configuration/identity and selected authorized-key files; account private keys need their own secure custody. A rebuild must decide explicitly whether to preserve the old host identity or introduce a new one and verify fingerprints.

## Maps and household backups

The maps block of dataark.yaml enables monthly checks (refresh_days 30), reserve_gib 10, max_run_gib 8 and configured flood/parcels/topographic sources. Coverage is Massachusetts, Worcester and Middlesex counties, with Northern Worcester as the descriptive focus. Geographic scope is not a promise of complete data or an interactive basemap. See [Local reference maps](Maps.md) for downloader/coverage limits and service setup.

Household configuration is a separate bugout block with source-specific credentials and normal maintenance/bugout policies. The current configured manuals source uses daily prefetch; do not publish its actual credentials or assume an integration token exists merely because example HA YAML is present. See [Household backups](Bugout.md) for state, outbox, encryption and cancellation semantics.

## Diagnostics, permissions and configuration capture

Debug is represented by /var/lib/ark/debug_status. The common structured event stream is /var/lib/ark/events.log and exposed through /api/events. Library basic outcomes are recorded with Debug off; extra stages and coarse progress require Debug. Authentication headers and raw request bodies must not be logged.

dataark-portal-monitor.service runs a bounded metadata capture only while Debug is on. Its root-only log directory is /var/log/dataark-portal-monitor. The service limits CPU to 5 percent, memory to 64M, uses Nice=10 and restricts writable paths and capabilities. Four rotated 1 MiB files bound its local capture. The packet monitor is not the library application log.

Run tools/capture_config.py as root before significant changes. Its root-only archive contains sensitive settings, SSH host identity and Samba state; never commit or publish it. The capture now includes FTP, root helper copies, boot configuration, live manifest, package/dependency inventory, container inspection and repository revision/dirty status as well as the earlier network/web/service settings. Content libraries and source/private keys outside the listed scope still require separate backups.

## Known reconstruction gaps

Existing installers cover feature-specific configuration but do not fully provision a clean Pi image. The base image, API unit/vhost creation, Docker/image pinning, physical interface mapping, user creation, storage provisioning and full rebuild validation need integration into the bootstrap described in [Bootstrap plan](../30-Developer/BootstrapPlan.md). The settings above are an observed reference, not a fully tested reinstall recipe.
