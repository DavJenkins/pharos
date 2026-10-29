# Architecture

## Request paths

Browsers reach Apache on port 80. Apache serves generated/static files from /var/www/html and proxies /api/ to FastAPI on loopback port 8000. FastAPI routers validate requests and delegate to services. Collectors obtain network, platform, resource, and service information from Linux. The dashboard consumes the API; its ordinary status requests do not execute arbitrary commands. The separately authenticated browser terminal follows a different path, described below.

Kiwix is a separate container on port 8080, mounting the content SSD as /data. ZIM reader links use the current browser host with the configured Kiwix port. Apache's /library-files/ alias and Samba's Offline-Archives share expose public original files. Anonymous FTP uses a read-only service mount of the public library. SFTP and rsync over SSH use existing Pi account permissions.

The browser terminal uses Apache HTTPS on port 4200, proxied to an unprivileged loopback-only terminal backend on 4201. That backend opens a fixed SSH connection to the existing Linux admin account, requiring its Linux password. This is separate from the public dashboard/API and shared caretaker authentication. See [Browser terminal](../20-Administration/BrowserTerminal.md).

## Source and generated output

- app/main.py registers the active FastAPI routers. app/routers contains HTTP boundaries; app/services contains policy and implementation helpers; app/models defines typed status contracts.
- app/templates/index.html is the dashboard source template. app/static contains browser assets and generated index.html.
- config/library/ark.yaml and its collection/catalogue files are the public authoring project. dataark.yaml remains the runtime compatibility manifest and can include private household tasks; public exports exclude those private sections. See [Modular configuration](../20-Administration/ModularConfiguration.md).
- tools/render_dashboard.py validates the manifest and renders the dashboard. It does not download content.
- tools/publish_docs.py converts docs Markdown to local HTML. deploy/deploy-web.sh builds and publishes both site and docs.
- deploy contains explicit installers for root helpers, services, networking, and distribution configuration. Editing source alone does not update an already installed root helper.

Do not infer active behavior from every file present: legacy modules and scripts may remain. Trace imports in app/main.py, the live systemd unit, and Apache configuration.

## Network roles

The hotspot uses 192.168.4.1/24. The built-in radio (normally wlan0) is the default hotspot, but either AP-capable Wi-Fi adapter may be assigned; the other handles optional upstream Wi-Fi. `tools/wifi_interfaces.py` resolves current roles from `/run/dataark-wifi-roles.json`. Ethernet is another upstream route. Local library access is independent of upstream connectivity. Internet pass-through is per-device state, normally with a six-hour limit and reset on reboot.

The portal intercepts known HTTP connectivity probes and uses trusted peer information supplied by Apache. The API must stay loopback-bound; untrusted callers must not be able to forge the peer header by reaching it directly. Client captive-portal behavior is not fully controlled by the server.

## Privilege boundary

The API runs as admin. Network, pass-through, library, and household operations use fixed-scope helpers with validated inputs and narrowly scoped installed permissions. Library and network management share a salted password hash in /etc/dataark/network-admin.json. Public reading is independent of that credential. SSH and Samba accounts have their own credentials and permissions.

HTTP remains available for local management; optional HTTPS can also be configured. HTTP forms have no transport encryption. Preserve the intended local deployment boundary. Logs must never include submitted credentials, authorization headers, or raw request bodies.

## Update and removal transactions

The content updater serializes work with worker.lock, checks trusted publisher metadata, resumes staged downloads, verifies hashes, then invokes activation. Activation checks the reader catalogue before retiring a prior archive. Hidden staging and journals support recovery after interruption. Avoid changing the manifest while the updater holds its snapshot; it detects configuration changes and can abort activation.

Removal takes the same worker lock, stages the registered file, disables its updates, refreshes the reader/catalogue, then deletes the staged file after commit. Retained removed records permit supported reinstatement. The updater attempts removal-journal recovery before ordinary work.

Map maintenance and household snapshots are separate workers with distinct policies. A link in resource_sections is an index entry, not a job definition. A public collection is not automatically a household backup task.

## State and observability

State under /var/lib/dataark tracks updater, maps, portal, and household work. /var/lib/ark contains the Debug flag and common event log. Library events correlate operation stages and record outcomes; extra stages follow Debug. Portal packet metadata is a separate rotating capture. Logs and process activity do not replace end-to-end reader or restore tests.

## Known boundaries

No anonymous rsync daemon or WebDAV service is configured. A Massachusetts OpenStreetMap-derived vector basemap now has a local browser viewer; it does not provide search or route planning. Flood/parcel GIS datasets still need an external viewer. Public library requests, storage-based approvals, a full recovery image, and comprehensive client/offline acceptance remain unfinished work.

## Peripheral resource principle

The network, Linux computer, storage, terminal, tools and physical interfaces incidental to serving content are potential resources under adverse conditions. Their utility is not limited to administration. Discoverability, offline dependencies, access requirements and operational limits belong in the [resource guide](../10-User/Resources.md). Preserve open library access and continuity when adding features. Workload quotas, isolation and public compute are not automatically provided by this architecture; they must be separately designed and verified.
