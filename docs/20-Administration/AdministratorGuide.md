# Administrator Guide

## Capture the appliance configuration

Run on the Pi from `/opt/dataark`:

    sudo python3 tools/capture_config.py

The script creates a timestamped root-only directory under `/var/backups/dataark/`.
It stores `configuration.tar.gz` and `inventory.json`. Both are private: network,
Samba, service, and container settings can contain passwords. Do not commit them
or upload them to a public issue. The terminal summary is safe to share.

The capture includes installed service inventory, the Data Ark unit, network
addresses and routes, firewall rules, mount information, listening ports,
container summaries, and selected configuration directories. Missing commands
are recorded without preventing the rest of the capture. Inspect reported errors.

This is a configuration snapshot, not a complete recovery image. ZIM archives,
PDFs, repository contents, installed binaries, container volumes, and targets of
external symlinks need separate backups. Copy private backups to secure separate
storage; keeping the only backup on the Pi does not protect against disk failure.

## Deploy repository changes

Run on the Pi:

    cd /opt/dataark
    ./deploy/deploy-web.sh
    sudo systemctl restart dataark.service
    systemctl status dataark.service --no-pager

Then reload the browser with Ctrl+Shift+R. Verify `/api/status`, `/docs/`, and
`/logs.html`. If the API fails to start, inspect `journalctl -u dataark.service -n 50`.
Run the regression checks before deployment with:

    venv/bin/python -m unittest discover -s tests -v

## Status meaning

The dashboard prefers the content updater activity when available: queued/checking, downloading, verifying, activating, publishing, waiting, failure or idle. Its separate legacy sync collector can report rsync process activity. Neither idle nor a process name alone establishes archive freshness or successful completion. See [Library management](Library.md) for the current lifecycle and diagnostics.

Health is `degraded` at CPU temperature 70 C or filesystem usage 80 percent,
and `error` at 80 C or 90 percent. These thresholds carry forward the previous
collector's policy and are not a hardware diagnosis. Missing readings and
non-running monitored services produce `degraded` with an explanation.

Monitored services are the API itself, Apache (`apache2.service`),
NetworkManager, and Samba (`smbd.service`), based on the existing deployment.
Kiwix is checked through its HTTP homepage at `127.0.0.1:8080`, with a two-second
socket timeout and a bounded response read. It must return HTTP 200 and the
verified Kiwix page title. A changed/customized title requires updating the probe.
Archive integrity, captive portal behavior, and actual client network
reachability are not yet health probes. A running service is not an end-to-end test.

Unavailable collector sections and missing numeric measurements are null.
The storage collector expects the SSD to be mounted at `/mnt/storage`; it will
not report the root filesystem's usage as SSD usage when that mount is absent.
The browser clears stale status indicators if a request fails or times out.

## Offline acceptance check

From a phone attached to DataArk Wi-Fi, with the Pi's upstream disconnected:

- Confirm captive portal discovery and manual access to the local dashboard.
- Open local archive content, PDFs, documentation, and file shares.
- Confirm the dashboard updates and reports failures honestly.
- Keep intentional off-device reference links; those require internet access.
- Reconnect upstream after the check.

Do not change networking remotely until there is a local recovery path.

## Recovery

Inventory capture is the first step; a full rebuild procedure still needs the
captured configuration and a tested restore on spare storage. Do not extract
the archive over a running system without reviewing the files and paths.


## Network administration setup

Run once on the Pi, and after changes to the helper:

    sudo python3 deploy/install_network_admin.py

The installer asks for a separate network administration password on first run.
Existing credentials are preserved on reinstallation. It installs a root-owned
helper and a sudo rule permitting only that helper with no command-line arguments.
It does not change or restart network connections. Only a salted password hash
is stored under /etc/dataark; this is not your Linux or Wi-Fi password.

Run the tests, publish the website, and restart dataark.service as described above.
Open /config/wifi.html or /config/system.html and enter the new password.
Legacy CGI scripts are no longer used. Do not enable CGI or grant general nmcli
sudo access to the API. The shared password prompt can optionally cache authorization in tab-scoped session storage for a chosen fixed duration. See [session behavior](Library.md#session-behavior); use Lock now or the floating padlock to clear it.

HTTP administration credentials and submitted Wi-Fi passwords are not encrypted
in transit. Optional HTTPS is documented in [HTTPS](HTTPS.md). Use a trusted local connection;
do not expose these administration endpoints to the internet.

The helper scans/connects only on the assigned upstream Wi-Fi radio and renames
only the DataArk profile after verifying the assigned hotspot is in AP mode. Open and WPA/WPA2 Personal are supported;
WPA3-only and enterprise networks require local configuration.
SSID length is checked in UTF-8 bytes. Passwords go through stdin and a private
temporary password file, never shell interpolation, process arguments, or logs.

Each upstream connection attempt creates a new profile, with autoconnect enabled
only after success. Existing profiles remain intact; review obsolete generated
profiles locally when appropriate. On failure the helper attempts to restore
the previous connection and remove the new profile. Failed AP renames similarly
attempt to restore the previous name. Recovery is best effort; keep console access.

Validate scanning first. Test actual connection changes and AP renaming at the
Pi console, then verify reconnect and reboot persistence. Automated tests mock
NetworkManager and do not disrupt the live network.

Command reference:
[NetworkManager nmcli manual](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html).


## Content access and SSD portability

The content SSD is the exFAT volume OfflineRepo, mounted at /mnt/storage.
ZIM archives and portable reader folders are stored on the SSD. Use Manage Library for the current inventory; installed titles change. Do not move archives or reformat the drive to install these changes.

Run on the Pi:

    sudo python3 deploy/install_content_access.py

The installer verifies the mounted SSD, creates portable orientation files,
backs up server configuration under /var/backups/dataark-content, validates the
Samba candidate and Apache configuration, and reloads both services. Configuration
is restored if validation/reload fails; generated orientation files remain.

Offline-Archives is corrected to /mnt/storage and explicitly read-only.
Both content shares use the existing admin Unix account instead of the unverified
pi account. The separate Bugout-Staging share retains its existing write policy.
The dataark source-code share is preserved. Windows clients can use their existing
Samba login; guest access depends on client policy and is not guaranteed.

Apache exposes /library-files/ as static files with directory browsing. Executable
handlers, .htaccess overrides, and symbolic-link following are disabled there.
The staging directory and system metadata directories are denied over HTTP and
excluded from the read-only library share. No CGI module is required.

At the SSD root, START-HERE.html uses relative links and needs no API, server, or
internet connection. README-DATA-ARK.txt supplies plain-text instructions.
DATA-ARK-CATALOG.json records file paths and sizes, excluding uploads and system
metadata. The generator refuses to overwrite unrelated orientation files.

Refresh the catalog after adding curated content:

    python3 tools/publish_content.py

Optionally generate SHA-256 hashes by reading all content (potentially hundreds of GiB):

    python3 tools/publish_content.py --checksums

Hashing is not part of normal installation. A normal refresh replaces the
catalog with metadata only. Retain a copy of a hashed catalog if needed.
Checksums detect changes, not correctness or provenance of the source material.

For direct access, shut the Pi down cleanly before disconnecting the SSD. Attach
it to another computer, mount OfflineRepo, and open START-HERE.html. exFAT supports
Windows/macOS interchange; a compatible reader is still needed for each format.
Windows Kiwix programs are cataloged when found, but their compatibility and
readers for other platforms remain to be tested.

Verify after deployment: browser reading through Kiwix; a small file download
through /library-files/; read-only SMB access; separate staging uploads; and finally
direct SSD access while the Pi is shut down. Do not test writes against an archive.

Sources:
[Apple filesystem formats](https://support.apple.com/en-tm/guide/disk-utility/dsku19ed921c/mac)
and [Samba configuration reference](https://www.samba.org/samba/docs/current/man-html/smb.conf.5).

The content catalog also supports an empty SSD. No preloaded library or ZIM archive is required. Checksums are optional and are never generated by installation or the normal catalog refresh.

## Library and FTP administration

See [Library management and distribution](Library.md) for authentication, removal/reinstatement, worker journals, lifecycle logs, FTP installation and public transfer methods. Do not put the shared password in documentation. Keep credentials and configuration snapshots outside the public library. FTP and SMB expose the public library; they are not configuration-backup targets.
