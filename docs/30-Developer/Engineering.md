# Engineering behind the Ark

*Companion to [What the Ark can do](../10-User/FeatureCatalogue.md) · Architecture and design*

The collection tells you what the Ark holds. The feature catalogue tells you what people can do with it. This chapter describes the less visible engineering that makes those capabilities possible: how the Ark represents intent, protects working content, handles interruptions, preserves open access and prepares to reproduce itself.

These are distinctive combinations and design decisions in this project, rather than claims that the underlying algorithms or techniques were invented here. Recovery validation and its acceptance criteria are documented separately in [Recovery validation](../20-Administration/RecoveryValidation.md).

## 1. Configuration describes the appliance, not just its settings

The public authoring project describes collections, their presentation, sources and acquisition policy. A card's existence, artwork, links and registered assets derive from that configuration. The community card has its own visibility option. Personalization can describe vehicles, jurisdictions and destinations without putting those choices into application code.

The authoring project is split into readable files and folders rather than requiring a person to maintain one enormous YAML document. The runtime compatibility manifest is assembled from that project; private household tasks are excluded from public exports. Generated pages and indexes are outputs of the configuration, rather than a second independently maintained inventory.

**Why it matters:** a replacement drive can inherit the intended library even when the files themselves are absent. The same description supports presentation, management and restoration.

See [Modular configuration](../20-Administration/ModularConfiguration.md) and [Configuration reference](../20-Administration/Configuration.md).

## 2. Extension types use a documented contract

Content types are registered through a shared type registry. Built-in and additional types use the same defined interface for their handlers; a new kind of resource does not require another special case scattered through the dashboard.

The public configuration selects supported handlers and supplies data. It does not become an unrestricted container for executable Python. Adding executable behavior remains a deliberate software installation and review step.

**Why it matters:** extensibility remains understandable without giving a public configuration editor arbitrary command execution.

See [Architecture](Architecture.md) and [Configuration reference](../20-Administration/Configuration.md).

## 3. Configuration editing is a publication transaction

The browser editor separates public reading from authorized writing. File and section selection, syntax coloring and validation make the authoring project inspectable without a caretaker password.

Publishing uses revision checks, validation, worker coordination and retained snapshots. A stale editor cannot silently replace newer configuration; concurrent maintenance and unexpected source edits are handled as conflicts rather than overwritten. Private rollback material stays outside public downloads.

**Why it matters:** configuration is operational state. Saving it must preserve a working appliance, not merely write a text file.

See [Modular configuration](../20-Administration/ModularConfiguration.md).

## 4. Updates protect the last usable copy

Acquisition is a staged operation: queue, download or resume, verify, activate, refresh the reader and finish. Worker locks serialize conflicting work. Activation checks the reader catalogue before retiring the prior archive; configuration changes during a worker's snapshot can prevent unsafe activation.

Removal uses the same coordination and a journal: stage the registered file, update its selection and catalogue, then complete deletion after commit. Retained source records distinguish deliberately removed content from content that should simply be fetched again. Interruption recovery examines the removal journal before ordinary work resumes.

**Why it matters:** a failed transfer, failed publisher check or interrupted removal should not casually destroy the last working library.

See [Library management](../20-Administration/Library.md) and [Architecture](Architecture.md).

## 5. Publisher checks distinguish freshness from availability

Check intervals mean “look for a publisher change,” not “a new edition will exist.” The system records last checks, next due times, changed sources and failures separately. Reviewed discovery rules can follow predictable dates, years and filename patterns rather than assuming every publication has a permanent URL.

A failing source does not invalidate the saved copy. Human-captured files establish their own identity, edition and checksum baseline, so a successful import can resolve an acquisition gap without pretending future automatic updates are guaranteed.

**Why it matters:** an offline archive needs honest provenance and freshness information, not a binary online/offline label.

See [Source availability checks](../20-Administration/SourceChecks.md) and [Browser capture](../20-Administration/BrowserCapture.md).

## 6. Browser capture validates content before installation

The capture extension bridges a publisher page that works interactively and an importer that must place files consistently. Pi Chromium can use a narrowly scoped native helper; the desktop workflow can pair through SSH.

The importer validates selected supported downloads, maintains source records and indexes, and retains the previous bytes outside the public tree when replacing material. It is not an indiscriminate browser-download mirror or a route for publishing completed private forms.

**Why it matters:** a person can supply the missing browser interaction without becoming responsible for the Ark's internal file layout.

Publisher-hosted HTML introductions can be retained as attributed, checksummed snapshots when an old PDF URL is no longer usable. Their recipe preserves the captured text, source URL and capture time. A caretaker can compare the current publisher page with the saved copy and record an unchanged review tied to that copy’s hash. This advances a review deadline without downloading, rewriting or claiming byte-for-byte automatic verification of the publisher page. Missing or changed local bytes invalidate the acknowledgement.

See [Browser download capture](../20-Administration/BrowserCapture.md).

## 7. Recovery preserves intent across two replaceable halves

The design treats the system medium and content medium as separately replaceable. Public configuration mirrors, source checkpoints, software-baseline information and content profiles accompany the recovery tools. A populated content drive and a configuration-only seed are both meaningful inputs.

The stock-Pi setup path turns a supported running Debian-based Pi into an Ark through explicit setup steps rather than requiring a clone of the original system image. Device-specific private identity is separate from the portable public description.

The coordinator uses platform profiles for the Pi and generic Debian 13 ARM64/x86-64 LAN machines. Read-only discovery binds reviewed roles to hardware identities; LAN profiles retain the host’s existing network configuration and network manager, including systemd-networkd; they do not require NetworkManager or install a hotspot. Architecture-specific PMTiles and Kiwix pins prevent shipping the source machine's binaries indiscriminately. See [Platform flavors](PlatformProfiles.md).

Drive replication adds a capacity-aware file-copy plan rather than a block image: configuration only, whole collections that fit, or all public content. The exact reviewed plan binds public configuration, source revision, selected file sizes/timestamps and destination UUID. The terminal worker protects backing disks, coordinates with content workers, checks partial prefixes before appending and records SHA-256 verification receipts. Its portable catalogue includes only verified copied payloads, while its recipe preserves full restoration intent. See [Clone a content drive](../20-Administration/CloneDrive.md).

**Why it matters:** the desired end state is understandable and reproducible, rather than existing only as the accidental contents of one working machine.

Validation records cover [clean generic ARM64 installation](../20-Administration/CleanBootstrapTest.md) and [frozen-kit replay](../20-Administration/FrozenBootstrapReplay.md), including package installation, services and reboot checks. Physical Pi acceptance is documented separately.

**Acceptance boundary:** these mechanisms do not yet establish dependable two-way regeneration. Fresh-system, spare-media and interruption acceptance remain required.

See [Paired-media recovery](../20-Administration/PairedRecovery.md), [Stock-Pi setup](StockPiSetup.md) and [Recovery validation](../20-Administration/RecoveryValidation.md).

## 8. Restoration is a persistent capacity-aware plan

None, Minimal, Recommended and Full presets are evaluated against the saved selection and destination capacity. Planning includes installed size, temporary staging, growth, update headroom and a free-space reserve. Unknown sizes block approval instead of counting as zero.

Dependencies precede their dependents, small independent packages can run before large ones, and indexes run last. Approval is tied to the reviewed plan's identity. The persistent queue supports pause, cancellation, retry and resumption; the worker rechecks capacity before and during work.

**Why it matters:** restoring onto a smaller drive can be a deliberate useful subset, rather than an all-or-nothing download that fills the disk halfway through.

See [Capacity-aware restoration queue](../20-Administration/RecoveryQueue.md).

## 9. Networking protects the path used to administer it

Hotspot, upstream Wi-Fi and Ethernet have distinct roles. The API relies on trusted peer information from the loopback-bound Apache proxy, and guarded changes consider the access path in use.

Radio roles are resolved through persistent adapter identity rather than trusting that an interface name always means the same physical radio. Assignment changes have a confirmation window and rollback; the built-in adapter provides a fallback when the preferred USB radio is absent at startup.

Per-device internet pass-through is separate from local reading. Turning it on for one visitor does not silently open upstream access for everyone.

**Why it matters:** deliberate isolation and adapter changes need not mean losing the controls needed to reverse them.

See [Architecture](Architecture.md) and [AP welcome portal](../20-Administration/Portal.md).

## 10. Open reading and privileged operations have separate boundaries

The shared caretaker prompt is requested when an operation needs it, with an optional bounded authorization cache. Cache time is visible and can be cleared. A fresh-entry path exists for sensitive operations that must not reuse cached authorization.

The API delegates privileged actions to fixed-scope helpers with validated inputs and installed permissions. Linux terminal credentials, integration tokens and caretaker authorization serve different purposes. Read-only public distribution does not imply anonymous shell access or writable media shares.

**Why it matters:** protecting shared state does not require putting every reader behind an account.

See [Architecture](Architecture.md) and [Administrator guide](../20-Administration/AdministratorGuide.md).

## 11. Observability is layered and bounded

Basic operation outcomes remain available without enabling verbose Debug. Debug adds diagnostic stages and controls a separate rotating portal metadata capture. Bounded local records provide context without treating unlimited packet capture as the default.

Health reporting uses stable problem fingerprints so integrations can recognize an ongoing issue rather than announce the same fault on every poll. Support reports assemble build identity, system state and relevant diagnostics; credential stores and private household files are excluded, with recognized secrets redacted. A person reviews and sends the report.

**Why it matters:** useful evidence survives long enough to investigate a failure without making diagnostics an unbounded storage or disclosure mechanism.

See [Architecture](Architecture.md) and [Source and handover](../20-Administration/SourceAndHandover.md).

## 12. Visitor estimates do not require a visitor identity system

Web page views and file deliveries are counted separately. Daily unique estimates use salted digests with short retention. The all-time estimate uses a fixed-size HyperLogLog structure, rather than retaining an indefinitely growing list of visitor addresses.

The estimate measures observed addresses, not verified people: address changes, shared addresses and traffic outside the measured web path affect interpretation. Connected-device observations and historical web activity remain different measurements.

**Why it matters:** the Ark can show whether it is useful without adding reader accounts, tracking cookies or an ever-growing raw visitor registry.

See [Usage monitoring](../20-Administration/Usage.md).

## 13. Integration events can survive missed delivery

Collection/configuration changes have a bounded journal and operation identity. Home Assistant receives events while polling provides a fallback. Consumers can persist cursors and deduplicate operations; a journal gap is detectable rather than silently represented as complete history.

Bug-out controls have their own integration-token scope. Event handling avoids feedback loops and does not depend on Debug being enabled. Delivery is not claimed to be exactly once; consumers must tolerate repeated events.

**Why it matters:** another appliance can act on Ark changes without assuming every network request succeeds at the first attempt.

See [Architecture](Architecture.md) and [Household bug-out backups](../20-Administration/Bugout.md).

## 14. Anonymous participation has recoverable personal control

Community posts use public permalinks. An author's private deletion capability is carried in a bookmarkable URL fragment, while the server retains a hash of the deletion code. Opening that link previews the action; it does not immediately delete a conversation.

Caretaker edits are marked. Restore operations validate the backup, provide a preview, check for stale state and retain a safety copy. Markdown and banner variables are rendered through constrained paths; code and link destinations are not treated as greeting-variable substitutions.

**Why it matters:** useful local collaboration can avoid mandatory accounts while retaining authorship controls, visible moderation and deliberate restoration.

See [Community board and announcements](../20-Administration/CommunityBoard.md).

## 15. A software test Ark can borrow the real collection safely

The desktop ARM64 guest has its own operating-system disk, runtime databases, credentials and loopback-forwarded services. It mounts the real media through a read-only share and a read-only guest mount, so a second full copy of the collection is unnecessary.

A separate guarded application entry point rejects physical-network, media-restoration and household mutations. The emulator can exercise real archive pages and map byte-range delivery without pretending to emulate Pi radios, USB behavior, captive-portal clients or physical power failures.

**Why it matters:** realistic software experiments become possible without treating the working appliance or its media as disposable test fixtures.

See [Desktop ARM64 test Ark](../20-Administration/Emulator.md).

## 16. Software changes are signed, journaled transactions

The software updater separates public release discovery, caretaker authorization, root-owned signature verification and a fixed systemd worker. The release-signing key is independent of the caretaker password. A package is an explicit file inventory, not an executable installation script: platform, base revision, dependency lock, schema and local-file hashes must match before installation begins.

The worker snapshots affected software and build metadata, writes a durable transaction journal, and stops the API before replacing files. Health failure restores the prior files and identity. An interrupted transaction is restored before the API starts at boot, with health verification deferred until services are available. A transient root-owned runtime marker separates a legitimate update restart from boot recovery; it disappears on reboot. Schema, dependency, OS, network and privileged-helper changes are deliberately outside this first software-only package contract.

**Why it matters:** an offline, already acquired update can use the same verification path as an online release, while the content drive, personalized configuration and credentials remain outside the update payload. Recovery is part of the transaction rather than an instruction to reinstall after a failure.

Acceptance includes real API stop/start, automatic rollback of an invalid API release, an interrupted worker process, restore-before-startup and post-recovery checks in the disposable ARM64 QEMU Ark. Physical-media and schema-migration acceptance remain separate.

See [Software updates and maintenance](../20-Administration/SoftwareUpdates.md).

## 17. Deployment repeatability is tested, rather than assumed

A normal import can trigger web publication, so a live-only correction is insufficient: the deployment source must retain it too. Shared status, capture styling, library contrast, branding links and backup actions are kept in the source used by subsequent publications.

The release audit runs the actual deployment script in a private mount namespace. Its source and web paths point to an isolated checkout and staging destination, with the real content mounted read-only. Assertions verify the expected interface contracts after deployment. Read-only HTTP checks exercise local landing-page destinations, actual Kiwix entry pages and representative reader resources. Anonymous mutation requests verify caretaker boundaries without performing destructive actions.

The bootstrap kit carries a validation record tied to its exact source revision. The record distinguishes web deployment and reader checks from clean-OS installation and physical-media recovery tests. See the [validation report](../20-Administration/ReleaseAudit.md).

## 18. Hardware attribution follows observed hardware

“Powered by Raspberry Pi” is conditional on the machine’s reported device-tree model. A missing identity, generic ARM board or QEMU/server identity does not receive the badge. Platform capability discovery and this presentation check serve different purposes: choosing a compatible installer profile does not by itself establish hardware branding.

## 19. A system card can carry its own library and establish a new owner

A capped, preallocated ext4 image on the system card provides an independent content filesystem without an external disk. The grow operation verifies the recorded inode/device, mounted loop backing file and filesystem type before extending storage online. It preserves at least 10 GiB of system headroom and never shrinks or formats an existing library. The physical test card expanded from 4 to 80 GiB with all sample hashes preserved.

Recipient preparation separates software/content from the identity of the person who prepared the card. At recipient boot it replaces the hostname, machine/Ark identity and SSH host keys and removes the provisioner authorized keys. A four-digit pairing code gates first-owner setup through the browser; a root-owned, serialized helper persists failed attempts and a one-minute cooldown after five failures. Successful enrollment consumes the code and installs separate caretaker and Linux admin passwords. Root remains locked, with direct root SSH disabled. The local setup prompt dismisses itself if browser enrollment completes.

**Why it matters:** a prepared card can demonstrate the Ark offline, headless and without an external content drive or an activation service. A short pairing code establishes initial ownership without requiring a long transfer secret.

Physical acceptance exercised reboot into recipient setup, browser API enrollment and cooldown from a desktop on the LAN, new identity, password-based admin SSH, rejection of the old provisioning key, and healthy services. A real pseudo-terminal test verified prompt dismissal. This is distinct from a phone-over-hotspot client check and from an uninterrupted fresh-OS bootstrap replay. See [system-card library and recipient setup](../20-Administration/SystemCardLibrary.md).

### Guided provisioning across storage and ownership layouts

The same installation launcher performs discovery, storage selection, plan review and approval without requiring a copied command. Its saved site choices and installation journal bind resumption to the approved settings. A browser builds a portable card-preparation package; local Windows and Linux writers require explicit disk identity and erase confirmation and verify a pinned official OS image. A persistent first-boot service builds the Ark, installs only the fixed sample selection, prepares recipient enrollment and powers off on success. Initial installation needs internet; the prepared recipient appliance can start offline.

Recipient preparation covers managed full-library, system-card and LAN installations. It checks for inherited integration credentials and certificates, requires personal-file review, and generates a private printable welcome sheet. The running identity remains unchanged until the next boot. Public configuration does not carry passwords or private keys.

Library storage handover separates adopting a populated drive from replacing a missing drive. Adoption compares public configurations and verifies available recorded checksums without executing drive-provided code. Replacement retains the desired collection and optionally copies an available original before switching. A root-private journal snapshots configuration and the UUID mount selection before activation; failed or interrupted activation restores them. The management API does not depend on a successful library mount, so a missing drive can be diagnosed and replaced from the browser. Approved actions and outcomes enter the collection lifecycle feed for Home Assistant.

The provisioning regression suite passed 138 tests and 11 subtests on Linux. Four additional private-mount-namespace scenarios exercised real ext4 adoption, injected mount-failure rollback, empty replacement with a missing original, and copying an available original. These isolated tests formatted only temporary sparse images. The card writer's next physical replay remains part of media acceptance; an imaging success is not presented as a completed recipient appliance.

## 20. The library application can run independently of host administration

The Docker deployment separates public media, public configuration, durable application state and private credentials into distinct mounts. Its web/API process and Kiwix reader run as a non-root user without Linux capabilities, host networking, physical devices or the Docker socket. A foreground supervisor starts and stops the processes together and refreshes the configured reader set as media changes.

The same browser-facing address serves the dashboard, documents and Kiwix. The reader proxy streams bytes and preserves range responses needed by large archives and maps. Public file routing permits configured assets and the public-directory policy; it does not turn the entire mounted drive into an unrestricted private-file share. Container recreation retains the board, banner, caretaker record and public collection in their persistent storage.

Capability reporting distinguishes a container from a hardware appliance. Host network, disk and software-changing operations are rejected explicitly; absent systemd or Wi-Fi is not reported as a broken appliance. Configuration reload validates the mounted YAML and retains the last working manifest after invalid edits. [Container deployment](../20-Administration/Container.md) describes the operating boundary and host workflow.

## Maintaining this chapter

Keep this document focused on implemented mechanisms and the design reasoning behind them. Add source-specific contracts and operational instructions to the linked developer/admin guides. Record acceptance results in the validation documentation. The companion feature catalogue remains the account of what these mechanisms let people do.
