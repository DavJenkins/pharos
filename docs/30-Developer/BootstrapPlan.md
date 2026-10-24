# Reproducible image-to-Ark bootstrap

## Goal and present status

The intended installation experience is: flash a supported Pi image, boot with local access, run one bootstrap command, provide site-specific settings, and receive a working, verified Data Ark. Content can be selected/downloaded afterward rather than making a multi-hundred-gigabyte preload mandatory.

There is not yet a complete one-command bootstrap. Existing scripts install individual features on an already prepared appliance. Treating their concatenation as a clean-image installer would omit base users, disks, interfaces, API/vhost setup, Docker deployment and recovery validation.

## Supported baseline must be explicit

The reviewed host is Pi 4 arm64 running Debian 13 and Python 3.13.5. Select and test one exact Pi-capable image/release first. Document the image download, architecture, checksum, packages, firmware and hardware/network requirements. Do not promise that an arbitrary Raspberry Pi OS or Debian image will behave identically.

The existing hardware uses separate hotspot and upstream wireless interfaces. If a target Pi has only one Wi-Fi interface, the installer must require a suitable second interface or an Ethernet upstream, or explicitly support/test a different topology. Silent assumptions about wlan0/wlan1 are not acceptable.

## Inputs to collect

- Appliance name, timezone, regulatory country and intended local subnet.
- Chosen AP interface, upstream interface or Ethernet, hotspot name and privately entered network credentials.
- Existing content disk identifier, mount strategy and explicit confirmation if any destructive disk provisioning is requested. Default to preserving an existing disk.
- Administrator account and SSH/public-key policy, shared caretaker credential and optional Samba account settings.
- Library choices, geography, free-space reserve, optional household sources and separately entered integration credentials.
- Distribution options such as anonymous read-only FTP, with a clear public/private content boundary.

Secrets must come from private input or protected files, not command-line arguments, public YAML, logs or a downloadable build report. The repeatable public configuration should reference secret locations rather than contain actual values.

## Required phases

### Preflight and plan

Check hardware/architecture, image version, root privileges, clock, available interfaces/AP support, network overlap, storage identifiers/capacity and upstream access. Produce an intelligible plan before mutations. A non-mutating --check or --plan mode is part of the target design.

### Preserve and install base prerequisites

Take a private configuration snapshot when upgrading an existing appliance. Create the intended service account, install required distribution packages, fetch the selected repository revision and build the pinned Python environment. Pin/test container versions rather than relying on latest indefinitely.

### Storage and network

Mount the identified content disk with deliberate ownership/permissions and boot ordering. Do not format it by default. Configure the selected NetworkManager AP and upstream roles, hostname, time and forwarding policy. Keep console recovery available and warn before changing the current management route.

### Web/API and reader

Install the API service and Apache modules/vhost with a loopback-only backend. Install Kiwix container/compose configuration and prove an actual small test archive can be read. Deploy public original-file access and portable orientation files separately from staging/private areas.

### Feature installers

Integrate the reviewed feature installers rather than maintaining competing copies of their rules:

- install_network_admin.py: fixed network helper and private administration hash.
- install_content_access.py: Apache/Samba public content access and orientation files.
- install_pass_through.py and install_portal.py: default-off per-device forwarding and captive discovery.
- install_update_worker.py: manifest-driven reference-library queue and timer.
- install_library.py: authenticated collection selection/removal/reinstatement.
- install_map_worker.py: optional configured map maintenance.
- install_bugout.py: optional household source/backup integration.
- install_portal_monitor.py: bounded Debug-controlled portal diagnostics.
- install_ftp.py: optional anonymous read-only FTP.
- install_terminal.py: separately opted-in HTTPS browser shell with Linux authentication and reviewed certificate/network scope.

Each installer has prerequisites and possible effects. The bootstrap must encode their dependencies and re-entry behavior; this list is not an executable ordering guarantee. Network/firewall installers require especially careful recovery handling.

### Verification and report

Verify services and ports, manual hotspot access, a real client portal, the API, docs, public file download, a reader article and image, protected management, FTP/SMB where enabled, and staging exclusions. Test offline behavior independently of client cellular service. A running Docker process or HTTP 200 catalogue is not sufficient.

Emit a public summary of what succeeded, what is not installed and what remains blocked, plus a root-only detailed configuration inventory. Record image/package/repository/container versions and the intended site configuration. Do not report success when a required acceptance check failed.

## Safety, repeatability and upgrades

Rerunning should preserve content and credentials unless replacement is explicitly requested. Track managed files, validate candidates before switching them, keep rollback copies, and avoid broad firewall flushes or privilege grants. The installer must distinguish first install, repair and upgrade; it must not overwrite local changes invisibly.

Downloads need resume, free-space checks and eventual offline usability. An interrupted bootstrap should leave a clear journal/report and a documented continuation or rollback route. A dry-run cannot prove a dangerous action safe; destructive formatting and identity changes need explicit confirmation and device verification.

## Definition of done

The bootstrap is complete only after a person other than the original author can create an Ark from the documented supported image on spare media, using only the repository, private site inputs and instructions; pass the acceptance checks; rerun/upgrade without losing content; and recover from an interrupted installation. Until then, describe it as a plan or an experimental installer, not a supported one-command build.

## Next implementation milestones

- Capture a machine-readable site schema with secret references and validate its defaults.
- Provision the missing base/API/Apache/container steps using the reviewed reference settings.
- Add a non-mutating preflight and dependency plan.
- Wrap the feature installers with idempotent phase tracking and clear error/rollback reporting.
- Test on a spare SD and separate content disk, then perform an independent maintainer walkthrough.

See [Configuration reference](../20-Administration/Configuration.md), [Source and handover](../20-Administration/SourceAndHandover.md) and [Acceptance tests](../20-Administration/AcceptanceTests.md).

## Peripheral resource inventory

A future bootstrap report should list incidental usable capabilities alongside the primary library: installed tools, available local interfaces, access methods, offline dependencies and recovery instructions. Separate installed/tested functions from possibilities requiring more hardware or configuration. Do not silently enable administration, writable workspaces or code execution merely because the hardware supports them. Verify optional functions do not compromise content service.

## Reciprocal media recovery

The stronger acceptance target is two-way regeneration: original boot card plus replacement content drive, and original content drive plus replacement boot card. The desired content profile is now implemented under `config/content`; the public media mirror and source checkpoint support the reverse path, but do not yet supply a tested base-image bootstrap. See [paired recovery](../20-Administration/PairedRecovery.md) and `config/recovery.yaml`.
