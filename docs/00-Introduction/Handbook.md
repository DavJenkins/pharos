# Data Ark handbook and handover

[Browse the complete handbook](../SUMMARY.md)

## Purpose and scope

This handbook is the entry point for someone inheriting the appliance or returning to it after time away. It records the philosophy, intended behavior, deployed design, configuration dependencies, routine care and remaining work. It is also a navigation map to the more detailed guides, not a claim that every recovery scenario has been tested.

The core implementation and settings were reviewed on October 22, 2026; maps, forms, browser terminal and peripheral-resource guidance were updated on October 23, 2026. Dynamic facts such as installed collections, free space, addresses and job state belong in the live interface and private configuration inventory. Historic project notes must not be mistaken for current instructions.

## The central promise

Useful knowledge should remain accessible when the internet does not. A person nearby should be able to connect to the Ark, discover what is actually installed, and read it with minimal friction. The Ark is both a local server and a portable collection: the drive should remain useful without the original Pi.

The name and practical mission emphasize preservation, continuity and recoverability. Information should not depend on one person's memory, a single cloud account or an undocumented workstation. Maintenance knowledge belongs with the appliance as well as in its source repository.

## Philosophy and decisions

### Peripheral resources are part of the mission

The Ark exists to preserve and serve useful content, especially under adverse conditions. Under those conditions, capabilities incidental to that mission should be considered potential peripheral resources: the local network, Linux computer, terminal, storage, file-transfer services, installed tools and physical interfaces may solve problems beyond reading the library.

Make existing capabilities discoverable and usable without crowding out the library. Document what is available now, what requires authentication or additional equipment, what depends on upstream connectivity, and what is only a possibility. Useful peripheral functions are not limited to operating or maintaining the Ark.

Preserve the primary service while enabling this broader usefulness. Open reading and copying stay open to everyone. Authorization protects actions that can disrupt service, change shared state or destroy content; it is not a separate class of access to knowledge. Resource limits, isolation and recovery paths should be considered when adding a capability. These are design requirements, not a claim that all shell jobs are currently quota-limited or isolated from the library.

See [Resources beyond the library](../10-User/Resources.md) for the current inventory and practical boundaries.

### Open reading, shared stewardship

Anyone who can reach the public library should be able to read, search and copy it. Access does not require a personal reader account. Caretaking protects the common copy, storage and network configuration rather than granting a privileged class of readers.

Installed content can be removed only through an explicit, authenticated confirmation. Supported removed collections retain their source definitions and can be reinstated, including pre-seeded archives. Public requests for new collections and approval rules for large storage use are agreed goals, but the current implementation still requires the caretaker password for downloads and reinstatement.

### Show what exists

The landing page is for installed local holdings. A prominent online-only card is not a substitute for an offline collection. Manage Library is the place for available downloads, pending work, retained removed items and clearly labeled reference sources. A file transfer is not complete until integrity checks, reader activation and publication have succeeded.

### Consistent, touch-first controls

The gear groups the nine dashboard icons into Connections, Access and monitoring, and Support tools. A status/control icon opens details before an action; Help and Developer API are deliberately direct links. Desktop hover descriptions remain useful. Toggles belong inside the pop-up, Close belongs at the lower right, and duplicate titles and tiny separate information targets should be avoided.

System contains library counts, storage and activity beside Manage Library and the separately authenticated Terminal link. Internet pass-through means upstream access for the requesting hotspot device, not a global internet switch. Auto refresh controls the page's status polling, not system updates. These distinctions prevent a convenient-looking control from doing something surprising.

### Prefer recoverable transitions

Content operations validate identifiers and paths, serialize conflicting work, stage files, verify publisher hashes and check the local reader. Journals distinguish rollback from committed cleanup. Keep the previous working state until its replacement is confirmed. A successful process launch, API acceptance response or catalogue page is not proof of usable content.

### Separate public and private material

The public library, household backup credentials, upload staging, configuration snapshots and source checkout have different access rules. Do not publish a configuration archive or assume that all household material belongs in a public library. Installer defaults and public examples must not contain actual passwords or keys.

## What the appliance contains

The deployed hardware is a Raspberry Pi 4 Model B with 2 GB installed RAM and a separate exFAT SSD at /mnt/storage. Debian 13 on arm64 and Python 3.13 were observed on the reviewed host. The precise installed package list and kernel belong to a private capture; they are not a guarantee of compatibility with every Pi image.

Apache serves the browser interface, local documentation and public original files. FastAPI supplies status and management APIs. Kiwix provides ZIM reading. Samba and anonymous read-only FTP distribute public files. SSH/SFTP and rsync over SSH are account-based maintenance methods. Background systemd workers manage reference archives, map resources and household backup jobs.

The DataArk hotspot is available at 192.168.4.1/24. Wi-Fi adapter roles are configurable: the built-in radio is the default hotspot and the USB radio the default upstream client. Ethernet can also supply upstream connectivity. Captive-portal discovery helps a phone find the library; manual access to http://192.168.4.1/ remains essential. See [Wi-Fi adapter assignment](../20-Administration/WifiAdapters.md).

## Source code stays with the Ark

- [Canonical GitHub repository](https://github.com/DavJenkins/pharos)
- Local working checkout: /opt/dataark on the Pi.
- Local source share: enter \\dataark\dataark in Windows File Explorer, or smb://dataark/dataark in a compatible file manager. This development share has its own access permissions and is not the anonymous FTP library.
- The reviewed development branch is feature/readme-foundation. Confirm the actual branch and working changes before maintenance; do not assume GitHub's default branch matches the deployed checkout.

The GitHub repository is not automatically a backup of the working checkout. Git protects committed history; uncommitted configuration changes, ignored files, credentials, content archives and private operational state require separate handling. See [Source and handover](../20-Administration/SourceAndHandover.md).

## How to use and maintain it

- [User Guide](../10-User/UserGuide.md): connect, read, copy and interpret controls.
- [FAQ](../10-User/FAQ.md): authentication, download and format questions.
- [Library management](../20-Administration/Library.md): selection, removal, reinstatement, distribution and diagnostics.
- [Configuration reference](../20-Administration/Configuration.md): the settings and installed files needed to reproduce the deployment.
- [Administrator Guide](../20-Administration/AdministratorGuide.md): configuration capture, deployment, account boundaries and recovery precautions.
- [Source and handover](../20-Administration/SourceAndHandover.md): repositories, backups, credentials and transfer of responsibility.
- [Architecture](../30-Developer/Architecture.md) and [Developer Guide](../30-Developer/DeveloperGuide.md): implementation and change workflow.

Maps, household backups and portal behavior have dedicated guides in the [contents](../SUMMARY.md). Their rules are separate; a resource link does not create a synchronization job.

## What is working versus what is promised

Implemented capabilities include the offline all-50-state and Caribbean street-map viewer, the forms/reference collections, the authenticated HTTPS browser terminal, local library discovery, the management lifecycle, shared caretaker authentication, per-device pass-through, bounded portal capture, library lifecycle events, file distribution and documented configuration capture. FTP download/resume, blocked writes and private-path exclusion were verified on loopback and from the desktop LAN.

The reader audit identified archive-page timeouts even when the Kiwix catalogue was available. Do not mark all viewers healthy until actual articles and images pass. PDF and GIS formats differ: map indexes are not an integrated GIS viewer. Portable Windows software has its own execution/compatibility checks. See [Acceptance tests](../20-Administration/AcceptanceTests.md) for observed results and unresolved tests.

Other incomplete areas include a spare-storage disaster recovery test, public collection requests and storage approvals, some live household/encryption/HA checks, UPS-aware shutdown/eject policy and retention rules. No physical door, light or other home-automation actions are implied by a configured backup integration.

## The deployment goal

The intended end state is a supported Pi image plus one bootstrap command, site-specific input and a verified working Data Ark. Reusing installer scripts is necessary but not sufficient: the base image, disks, interface roles, Apache/API setup, container deployment, identity, credentials and acceptance tests must also be reproducible.

That is a goal, not an existing one-command installer. The [Bootstrap plan](../30-Developer/BootstrapPlan.md) records required stages, safeguards and acceptance criteria so the current appliance can be turned into a reproducible product rather than a collection of remembered fixes.

## Keep this record useful

Update the relevant guide, installer/template, configuration reference and acceptance evidence together when behavior changes. Record why a decision was made, not just its latest value. Keep dated incident findings distinguishable from permanent limitations. Never write that something is installed, live, complete or tested merely because code exists for it.

## Content gaps before the v1 baseline

The [content download gap register](../20-Administration/ContentGaps.md) consolidates unavailable files, rejected candidates, installed alternatives and unresolved needs. A download failure does not itself prove an uncovered subject, and a related guide is not necessarily an equivalent replacement.
