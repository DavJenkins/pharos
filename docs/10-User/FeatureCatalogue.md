# PHAROS Data Ark — What it can do

*Implemented features | October 28, 2026*

[Download the feature catalogue (PDF)](../../feature-catalogue.pdf) · [Companion: The Collection](CollectionCatalogue.md)

An offline library with the tools to connect, share, create, coordinate, maintain and rebuild. The Data Ark turns a small local appliance into a shared resource that remains useful when normal connectivity is unavailable.

A companion to The Collection. This document describes implemented software and configured capabilities, independent of which publications or datasets are installed. It does not repeat the content inventory.

## At a glance

1. Walk-up access without a reader account
2. Flexible connectivity and safe isolation
3. Several ways to take the knowledge with you
4. A dashboard that works by touch or mouse
5. System information and operational health
6. Usage history with bounded local records
7. On-demand caretaker authorization
8. Managed acquisition, removal and updates
9. Source checks and new-edition discovery
10. Human-assisted browser capture
11. Readable configuration and documented extensibility
12. Announcements that can reach an open browser
13. A local community noticeboard
14. PDF forms, coloring and drawing
15. Printables, games and practical browser tools
16. Household snapshots and bug-out controls
17. Home Assistant supervision and events
18. Recovery planning and reproducible selections
19. General computing and development on the Ark
20. Diagnostics, support and handover
21. A separate desktop ARM64 test Ark

## 1. Walk-up access without a reader account

*Power the Ark, join its network, and put a shared resource within reach.*

- A local Wi-Fi hotspot connects phones, tablets and laptops to the Ark without an upstream internet connection.
- Captive-portal discovery guides compatible devices toward the landing page; a fixed local address provides a manual route when a device does not open it automatically.
- The public library, documentation and ordinary browser tools are available without a caretaker account or an installed client application.
- The interface and its bundled fonts, scripts, icons and API documentation are served locally, rather than relying on a runtime CDN.
- A responsive landing page organizes collections and tools, provides recognizable artwork and local links, and keeps online references visually secondary.
- An intentionally separate caretaker role protects shared settings and storage while preserving open reading and copying.

[Operating details](../10-User/UserGuide.md)

## 2. Flexible connectivity and safe isolation

*Keep local service available while changing how the Ark reaches the outside world.*

- Ethernet and upstream Wi-Fi can supply internet while the hotspot continues serving local clients.
- Per-device internet pass-through lets an individual hotspot client use the available upstream connection without switching it on for everybody.
- Ethernet, upstream Wi-Fi and hotspot enable switches are accessible through their status pop-ups and require caretaker authorization.
- Current-access-path checks refuse network changes that would sever the management connection being used.
- Either supported AP-capable Wi-Fi adapter can serve the hotspot; the other can provide upstream Wi-Fi. The preference follows hardware identity rather than a fragile interface name.
- Adapter changes have a confirmation deadline and automatic rollback. The built-in radio provides startup fallback when the preferred USB adapter is absent.
- Hotspot naming and saved upstream connections have browser configuration pages. Disabling upstream links supports controlled isolation tests without unplugging cables.
- Optional public-domain HTTPS uses a DNS challenge and needs no inbound internet connection to the Ark. HTTP remains available; clones get separate certificate identities.

[Operating details](../20-Administration/WifiAdapters.md)

## 3. Several ways to take the knowledge with you

*Use the access method the available equipment supports.*

- HTTP serves individual files, browsable indexes and local collection pages. Byte-range delivery supports large map archives and compatible resumable clients.
- Read-only SMB and anonymous read-only FTP offer familiar file-copying routes. FTP supports passive transfer and denied writes.
- Authorized Linux accounts can use SSH, SFTP, SCP and rsync over SSH for maintenance and account-controlled transfers.
- A portable exFAT content drive includes orientation pages and a file catalogue for use on another compatible computer after a clean shutdown.
- The content share and retained staging share are read-only; the source-code development share is the deliberate writable exception.
- Reader programs and downloadable utilities can be distributed alongside documents without a cloud account. Compatibility and execution permissions still belong to the receiving device.

[Operating details](../20-Administration/Library.md)

## 4. A dashboard that works by touch or mouse

*Useful detail when it is needed, a compact status control when it is not.*

- The settings panel groups Connections, Access and monitoring, and Support tools, using consistent labels and touch-sized controls.
- Status icons open explanations and controls before changing state; Help and Developer API are direct links. Desktop hover text remains available.
- Healthy, idle status can condense to a green gear, with upstream-connection indicators and space for full activity messages when expanded.
- System, Library and Usage tabs separate machine information, collection management and activity. Tab bodies and controls have consistent sizing.
- Auto refresh is independently switchable with a saved browser interval from 5 to 300 seconds; it does not alter server download schedules.
- Pop-up switches, close buttons, page navigation and the shared navy-and-gold design provide consistent interaction across administration pages.
- Collection file counts double as expandable file lists, and grouped card actions use the same button treatment as ordinary collection links.

[Operating details](../20-Administration/DashboardCards.md)

## 5. System information and operational health

*See the machine, its workload and the problems that need attention.*

- The System view exposes hardware identity, installed RAM, usable memory information, uptime and current resource observations.
- Library summaries expose installed, pending and removed selections, storage capacity and current activity, with a direct management link.
- Service and health checks cover the API, web/file-serving components, reader availability and failed systemd units.
- Update failures, map-job problems, publisher-check failures and optional certificate health contribute to actionable health reporting.
- Build information includes the source revision, branch, source fingerprint and publication time, making local changes distinguishable from the last Git checkpoint.
- Optional HTTPS health warns as a certificate approaches expiry and reports expiry; the absence of optional HTTPS is not itself a fault.
- Health results distinguish warnings and errors, retain stable problem identifiers, and avoid treating a changed observation time as a new problem.

[Operating details](../20-Administration/Support.md)

## 6. Usage history with bounded local records

*Understand whether the Ark is being used without building a visitor-tracking service.*

- Connected-device information includes sampled hotspot clients and observations of SSH, VNC and browser-terminal connections.
- Hourly and daily activity buckets retain useful history: hourly observations for 30 days and daily aggregates for a year.
- Page views and file deliveries are counted separately; refreshing the landing page does not become a download.
- Qualifying web traffic is grouped by collection, with delivered bytes and daily activity views.
- Daily and all-time estimated unique visitors use address-derived private digests/sketches rather than cookies or browser fingerprinting.
- Public statistics omit visitor addresses, complete URLs, query strings and user agents; the monitor does not publish its private salts or sketch registers.
- The figures are activity estimates. Shared addresses, address changes, brief connections and traffic outside the monitored web path limit what they can establish.

[Operating details](../20-Administration/Usage.md)

## 7. On-demand caretaker authorization

*Make shared changes deliberate without repeatedly interrupting authorized work.*

- Protected actions request the shared caretaker password only when needed; reading configuration and ordinary public status does not prompt.
- An opt-in remember switch caches authorization for a chosen fixed 1-120 minutes, with 10 minutes as the default.
- The cache survives same-tab navigation and reload at the same Ark address, but its expiry is not extended by activity.
- An inline unlocked indicator shows remaining minutes. A floating red open padlock carries the remaining-minute count and locks immediately when tapped.
- Expiry, an authentication rejection or Lock now clears cached authorization. The server verifies each protected request.
- The shared authentication interface also provides a fresh-entry path for sensitive credential operations; it cannot reuse or renew the cache.
- Caretaker, Linux/SSH, Samba, Wi-Fi and integration credentials remain distinct. Optional trusted HTTPS protects management transport when configured.

[Operating details](../20-Administration/Configuration.md)

## 8. Managed acquisition, removal and updates

*Maintain a shared collection without confusing an accepted request with a completed installation.*

- Manage Library inventories installed, pending and removed items, their sizes, recorded source details, schedules and update state.
- Supported downloads progress through queued, downloading, verifying, activating and complete states, with explicit errors and recovery outcomes.
- The archive worker stages replacements, checks recorded sizes/hashes and activates verified files, retaining working copies during failures.
- Interrupted supported downloads can resume. Periodic publisher checks follow each configured interval rather than promising a new release on every check.
- Right-aligned trash-can actions identify the affected item and space, require explicit confirmation, and protect removal with caretaker authorization.
- Removal retains source definitions and changes the desired selection so routine updating does not silently put the item back.
- Supported removed or pre-seeded archives can be reinstated through verified download and activation. Unsupported types keep their recorded source/recipe for the appropriate restoration path.
- Collection lifecycle events record approval, stages, failure and successful installation; progress percentages do not masquerade as repeated installations.

[Operating details](../20-Administration/Library.md)

## 9. Source checks and new-edition discovery

*Know when an upstream source changes while preserving the copy that already works.*

- The landing page shows the last source-check time, relative age and a compact Check now control.
- Per-item schedules expose check interval, last attempt, next due time and results in Manage Library.
- Changed sources, new editions and failed checks are distinct review items; an HTTP failure never means the saved offline copy should be deleted.
- Reviewed release-family rules can find publications in predictably dated folders, filenames and links on approved publisher indexes.
- Format-aware checks validate documents/packages and use appropriate hash or metadata comparisons. Conditional requests avoid unnecessary repeated transfers.
- Publisher checks, archive updates and specialist map maintenance retain their separate schedules and behavior.
- Discovered editions are presented for review; reference checking does not silently promote every changed document into the installed collection.

[Operating details](../20-Administration/EditionDiscovery.md)

## 10. Human-assisted browser capture

*Bridge the gap between a public download that opens in a browser and a validated file on the Ark.*

- A capture page lists approved public-document targets that need manual browser acquisition or reviewed replacement.
- A Chromium extension on the Pi can hand a selected download to a narrowly scoped local importer without Windows pairing or a terminal password prompt for every import.
- A separate Chrome/Windows path can pair with the Ark through its native helper and existing SSH authorization.
- Capture is limited to the selected approved target; unrelated downloads and completed personal forms are not collected.
- Import checks file type, size, document identity/year and the expected destination. A stale replacement baseline is rejected.
- Imported files update source/provenance records, indexes, configuration and published pages. Previous verified bytes/metadata are retained outside public shares.
- Successful imports resolve the corresponding acquisition-gap entry. Original browser download files are retained rather than silently deleted.

[Operating details](../20-Administration/BrowserCapture.md)

## 11. Readable configuration and documented extensibility

*Keep the Ark understandable to the next person who maintains it.*

- A small main ark.yaml refers to separate collection definitions, publication catalogues, and generated version/order snapshots.
- The browser editor uses a folder-based file picker, section navigation, search, active-filename display, an unsaved indicator and offline YAML syntax coloring.
- Changing files clears old text while loading and resets section choices; a single section is automatically selected and disabled.
- Public configuration can be read, downloaded, inspected in History and validated without caretaker authorization. Saving and Community visibility require it.
- Validation checks syntax, duplicate keys, references and supported fields before publication. Revision checks protect against overwriting a newer configuration.
- Transactional publication preserves private settings, retains previous snapshots, keeps unchanged comments and rolls back handled publication failures.
- Personalization can record languages, jurisdictions, vehicles and destinations through validated references, without turning an interest into an automatic download.
- A shared content-type registry and documented handler interface provide an extensibility point. Handler code stays separately installed and reviewed rather than executable text hidden in public YAML.

[Operating details](../20-Administration/ModularConfiguration.md)

## 12. Announcements that can reach an open browser

*Put timely local information in front of the people using the Ark.*

- A caretaker-managed message-of-the-day banner persists through restarts until replaced or cleared.
- Safe offline Markdown supports headings, emphasis, lists, links, tables, code and line breaks, with a live preview.
- Background and text colors have pickers and hex fields; automatic contrast is optional. Font, width, side margins, vertical margins and placement are configurable.
- The banner can fit its text, span the available width or use custom side margins, and sit at the top, below the header or fixed at the bottom.
- Date/time formatting and greeting variables cover today, tomorrow, weekday, daypart, next daypart, week/weekend and upcoming date ranges, using the viewing device clock.
- Recognized variables are bright green in the editor; unknown variables are red with a wavy underline and remain literal in published text.
- An optional Broadcast action sends an updated message as a dismissible pop-up to other open Ark HTML clients. The sender suppresses its own alert, and acknowledged alerts do not repeat on reload.
- Broadcast is local browser delivery, not guaranteed delivery to disconnected devices or an operating-system push-notification service.

[Operating details](../20-Administration/CommunityBoard.md)

## 13. A local community noticeboard

*Coordinate without requiring an online social network.*

- Visitors can read and post announcements, requests, offers and discussions without an external account or email address.
- Nested Reply actions preserve conversation relationships, with restrained indentation on narrow screens.
- Messages support safe Markdown, formatting help and optional preview; titles and display names remain plain text.
- Every message has a public permalink. A private preview/delete link lets an author bookmark control of their own message without creating an account.
- Opening a removal link never deletes immediately. Deletion requires explicit confirmation; root removal includes its conversation, while removing a reply preserves its descendants.
- Caretakers can remove or edit messages; changed messages show an Edited by caretaker marker and edit time. Stale edits are refused.
- Rate and capacity limits bound posting. Display names are unverified; no private-message or attachment service is implied.
- Daily private snapshots, downloadable backups, validated restore previews, stale-preview protection and pre-restore safety copies protect the board and banner.
- Community visibility can be disabled in the public configuration without deleting messages or automatically disabling the direct board address.

[Operating details](../20-Administration/CommunityBoard.md)

## 14. PDF forms, coloring and drawing

*Turn the browser into a useful local work surface.*

- A local PDF form tool opens a user-selected PDF, supports interactive form-field types and can add visible writing to a page.
- Completed work can be downloaded or printed; user files are processed in the browser instead of becoming public library uploads.
- The coloring/drawing tool opens a library PDF, a personal PDF or a blank canvas, with page navigation, color selection, brush and eraser.
- An enclosed-area fill tool protects dark outlines; brush size controls how narrow an opening the fill can pass through.
- Undo and per-page clearing support experimentation without modifying the original PDF.
- Colored pages export as PNG images or through print/save-as-PDF. The output is an image of the work, not an assertion that editable PDF annotations have been preserved.
- Touch, pen and mouse interaction make the tools useful across phones, tablets and computers; work should be saved before leaving or reloading.

[Operating details](../20-Administration/FamilyResources.md)

## 15. Printables, games and practical browser tools

*Offer useful activities and calculations without a software installation.*

- Paper Studio generates customizable paper patterns and everyday worksheets, with A4/US Letter, portrait/landscape, printing, save-as-PDF and SVG export.
- Pattern controls support lined, square-grid, dot-grid, isometric, hexagonal, polar and other configured layouts, alongside ready-made print packs.
- Local browser games include memory pairs, tic-tac-toe, sliding puzzle and word hunt.
- Power planning tools total electrical loads and estimate battery/energy requirements from chosen assumptions; a separate micro-hydro calculator supports preliminary estimates.
- The local map viewer reads PMTiles using bundled scripts, styles, fonts and sprites, with pan, zoom, scale and configured geographic shortcuts.
- An amateur-radio practice tool supports question drill, immediate feedback, last-missed review, filtered rounds and practice exams with results.
- Callsign search supports prefix/name queries, grid-square proximity, distance, bearing and kilometre/mile display, using the saved database.
- Communicate runs as a local browser speech tool; a compatible device with an installed offline voice supplies speech. A preserved keyboard installer can be downloaded for use across Android apps.

[Operating details](../10-User/Resources.md)

## 16. Household snapshots and bug-out controls

*Prepare selected household files for loss of normal access.*

- Configured sources can be SMB shares, mounted local files/directories or HTTP files, with source-specific readiness and private credentials.
- Normal maintenance/prefetch can be manual, scheduled or refreshed on reconnection; its policy is separate from emergency bug-out inclusion.
- Bug-out operations support task priority, time budgets, progress, per-task results and cancellation, including configured continuation in the background.
- Operation identifiers deduplicate repeated trigger requests, and cancellation is offered for active work rather than an idle system.
- Portable tar snapshots and optional OpenPGP recipient encryption provide usable output; private decryption keys stay elsewhere.
- Staging, successful publication and replacement of normal prefetched copies are deliberate. Failed work does not silently become a successful snapshot.
- Live status reports readiness, bytes, outcome and event-delivery problems without returning source credentials.
- These are file snapshots. Consistency of changing applications/databases, restore verification and the publication/privacy of unencrypted output require explicit household choices.

[Operating details](../20-Administration/Bugout.md)

## 17. Home Assistant supervision and events

*Let a local supervisor observe and respond without making it a dependency for reading.*

- Home Assistant polls health, problem lists, optional certificate state and loss of contact, with stable change detection and recovery handling.
- Configured packages create/update persistent notifications and logbook entries rather than emitting the same unchanged warning on every poll.
- Authenticated integration controls can request and cancel bug-out runs without granting general Ark administration.
- Ark-originated bug-out events can inform household automation, with operation/event identifiers and safeguards against trigger loops.
- A durable collection/configuration journal reports lifecycle events, while percentage progress remains activity state rather than event spam.
- Persistent cursors support catching up within the retained window and report a feed gap rather than pretending missing history is complete.
- Phone notifications and physical-device responses remain household-selected automations. The public library continues operating when Home Assistant is unavailable.

[Operating details](../20-Administration/HomeAssistant.md)

## 18. Recovery planning and reproducible selections

*Carry the instructions for the library as well as its files.*

- Human-readable public profiles record desired content, sources, handlers, sizes/hashes and dependencies; absence on disk does not erase the intended selection.
- Public configuration and source checkpoints are mirrored onto the content drive, with software-baseline descriptions and source identity.
- Restoration can preview None, Minimal, Recommended or Full presets against destination capacity before approval.
- Capacity accounting includes staging, installed footprint, update headroom and a free-space reserve. Unknown sizes block approval instead of counting as zero.
- A persistent queue supports progress, pause, cancellation, retry and resume, with per-package verification and repeated free-space checks.
- Existing verified files can be reused, partial files are kept separate, and worker locks prevent competing download/activation jobs.
- Configuration-only and populated installation-drive preparation, START-ARK entry points and an experimental supported-stock-Pi coordinator are implemented.
- No automatic formatting or download approval is inferred. Full spare-media, fresh-Pi and interruption acceptance remain required before calling two-way recovery dependable.

[Operating details](../20-Administration/RecoveryQueue.md)

## 19. General computing and development on the Ark

*The appliance carries a computer that can help maintain itself.*

- An authenticated HTTPS browser terminal and normal SSH provide a Linux shell, with a welcome guide and ark-help topics for status, library, development, recovery and basics.
- WayVNC provides a local graphical desktop route tested from Windows over the hotspot and LAN. Installed RDP and AnyDesk remain additional options with their own acceptance/connectivity limits.
- The source repository, Git history, maintenance scripts, test suites and documentation are kept on the Ark, with GitHub as an additional remote reference.
- Python, its application environment, Git, compiler/build tools, archive utilities, curl, SSH and rsync support local maintenance and data work.
- Installed development applications include VS Code, GHex, OpenJDK and IntelliJ. The 2 GB board limits practical heavy-IDE use; installation is not a performance guarantee.
- The Codex command-line client is installed, with separate user sign-in. Hosted AI still requires an eligible account and internet; it is not an offline model.
- Public library use remains separate from shell/desktop account permissions. No anonymous general-code-execution service or complete offline package mirror is implied.

[Operating details](../30-Developer/DevelopmentTools.md)

## 20. Diagnostics, support and handover

*Give the next maintainer enough context to understand a failure.*

- Debug controls bounded local portal diagnostics and detailed lifecycle stages, while basic outcomes remain recorded with Debug off.
- Persistent system journals and rotating portal metadata logs preserve useful evidence with bounded storage.
- The local handbook, themed interactive API reference and documented handler interfaces remain available without upstream internet.
- A support composer collects a problem description, browser/build context and optional caretaker-authorized system/debug diagnostics.
- The report covers relevant resources, storage, failed services, network state, recent errors, update/source failures and available logs, recording missing telemetry instead of requiring everything to be healthy.
- Users can save a JSON attachment, open an email draft, or save a complete MIME .eml draft. Nothing is sent automatically; reports can be kept until internet returns.
- Credential stores, household files and message bodies are excluded from support collection; recognized secrets are redacted. Technical network details still deserve review before sharing.
- Source, private operational state and public configuration have separate handover and backup guidance, including remaining acceptance work.

[Operating details](../20-Administration/Support.md)

## 21. A separate desktop ARM64 test Ark

*Develop and inspect the software without experimenting on the live appliance.*

- A QEMU ARM64 guest runs the Ark software in a separate Debian system with its own disk, SSH key, caretaker credential and runtime database.
- The real media drive is mounted read-only over a read-only share, allowing the test instance to serve existing files without duplicating the entire collection.
- The dashboard, API, handbook, native Kiwix reader and real archive access operate through desktop loopback-only forwarded ports.
- A guarded emulator entry point blocks media mutation, physical-network, restoration and household control actions while permitting public reads and selected guest-local operations.
- Start, clean stop and SSH helper scripts, a readable profile and operating guide accompany the instance.
- The guest has been rebooted successfully with its services and media mount returning; real archive pages and map byte-range delivery were checked.
- This is a generic ARM64 software test environment, not complete Pi 4 hardware emulation. Radio, portal, USB/power and physical recovery acceptance remain physical-device work.

[Operating details](../20-Administration/Emulator.md)

## Practical limits

- Power, working storage/network hardware and compatible clients are still required. Captive-portal behavior and optional remote-access clients vary by device.
- Acquisition, publisher checks, hosted AI and certificate issuance require upstream connectivity when they contact outside services. Installed local material does not.
- HTTP remains available and is unencrypted; optional trusted HTTPS and separate service/account credentials have their own scope.
- The Pi has 2 GB installed RAM. Installed IDEs, services and viewers do not establish every workload, device or dependency has passed acceptance.
- Recovery tooling is implemented, but full spare-media/fresh-system acceptance and complete offline software provisioning remain unfinished. The emulator does not substitute for those tests.
- Usage measures activity and approximate addresses, not verified people. Broadcast reaches open compatible pages, not every disconnected device.
- Household data and support reports need deliberate privacy decisions. A backup is useful only when its independent restoration has been checked.

This catalogue describes the implemented capabilities at the edition date. The operating guides and configured hardware determine the available settings on a particular Ark.
