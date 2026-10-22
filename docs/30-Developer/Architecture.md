# Architecture

## Request paths

Browsers reach Apache on port 80. Apache serves generated/static files from /var/www/html and proxies /api/ to FastAPI on loopback port 8000. FastAPI routers validate requests and delegate to services. Collectors obtain network, platform, resource, and service information from Linux. The browser consumes the API; it does not directly execute privileged commands.

Kiwix is a separate container on port 8080, mounting the content SSD as /data. ZIM reader links use the current browser host with the configured Kiwix port. Apache's /library-files/ alias and Samba's Offline-Archives share expose public original files. Anonymous FTP uses a read-only service mount of the public library. SFTP and rsync over SSH use existing Pi account permissions.

## Source and generated output

- app/main.py registers the active FastAPI routers. app/routers contains HTTP boundaries; app/services contains policy and implementation helpers; app/models defines typed status contracts.
- app/templates/index.html is the dashboard source template. app/static contains browser assets and generated index.html.
- dataark.yaml identifies repositories, assets, update series, map coverage, resource sections, and configured household tasks.
- tools/render_dashboard.py validates the manifest and renders the dashboard. It does not download content.
- tools/publish_docs.py converts docs Markdown to local HTML. deploy/deploy-web.sh builds and publishes both site and docs.
- deploy contains explicit installers for root helpers, services, networking, and distribution configuration. Editing source alone does not update an already installed root helper.

Do not infer active behavior from every file present: legacy modules and scripts may remain. Trace imports in app/main.py, the live systemd unit, and Apache configuration.

## Network roles

wlan0 provides the DataArk hotspot at 192.168.4.1/24. wlan1 is the upstream Wi-Fi client. Ethernet may provide another upstream route. A hotspot client can use the library without upstream access. Internet pass-through is separate per-device state, normally with a six-hour limit and reset on reboot.

The portal intercepts known HTTP connectivity probes and uses trusted peer information supplied by Apache. The API must stay loopback-bound; untrusted callers must not be able to forge the peer header by reaching it directly. Client captive-portal behavior is not fully controlled by the server.

## Privilege boundary

The API runs as admin. Network, pass-through, library, and household operations use fixed-scope helpers with validated inputs and narrowly scoped installed permissions. Library and network management share a salted password hash in /etc/dataark/network-admin.json. Public reading is independent of that credential. SSH and Samba accounts have their own credentials and permissions.

Management is currently HTTP on the local network, so the application does not provide transport encryption for those forms. Preserve the intended local deployment boundary. Logs must never include submitted credentials, authorization headers, or raw request bodies.

## Update and removal transactions

The content updater serializes work with worker.lock, checks trusted publisher metadata, resumes staged downloads, verifies hashes, then invokes activation. Activation checks the reader catalogue before retiring a prior archive. Hidden staging and journals support recovery after interruption. Avoid changing the manifest while the updater holds its snapshot; it detects configuration changes and can abort activation.

Removal takes the same worker lock, stages the registered file, disables its updates, refreshes the reader/catalogue, then deletes the staged file after commit. Retained removed records permit supported reinstatement. The updater attempts removal-journal recovery before ordinary work.

Map maintenance and household snapshots are separate workers with distinct policies. A link in resource_sections is an index entry, not a job definition. A public collection is not automatically a household backup task.

## State and observability

State under /var/lib/dataark tracks updater, maps, portal, and household work. /var/lib/ark contains the Debug flag and common event log. Library events correlate operation stages and record outcomes; extra stages follow Debug. Portal packet metadata is a separate rotating capture. Logs and process activity do not replace end-to-end reader or restore tests.

## Known boundaries

No anonymous rsync daemon or WebDAV service is configured. OpenStreetMap is not yet an interactive offline basemap service. GIS datasets need an external viewer. Public library requests, storage-based approvals, a full recovery image, and comprehensive client/offline acceptance remain unfinished work.
