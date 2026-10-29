# Engineering behind the Ark

*Companion to [What the Ark can do](../10-User/FeatureCatalogue.md) · Implemented design, October 28, 2026*

The collection tells you what the Ark holds. The feature catalogue tells you what people can do with it. This chapter describes the less visible engineering that makes those capabilities possible: how the Ark represents intent, protects working content, handles interruptions, preserves open access and prepares to reproduce itself.

These are distinctive combinations and design decisions in this project, rather than claims that the underlying algorithms or techniques were invented here. Implementation is also distinct from acceptance: the recovery mechanisms below still require the documented spare-media tests.

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

## 6. Human-assisted acquisition still follows a controlled path

The capture extension bridges a publisher page that works interactively and an importer that must place files consistently. Pi Chromium can use a narrowly scoped native helper; the desktop workflow can pair through SSH.

The importer validates selected supported downloads, maintains source records and indexes, and retains the previous bytes outside the public tree when replacing material. It is not an indiscriminate browser-download mirror or a route for publishing completed private forms.

**Why it matters:** a person can supply the missing browser interaction without becoming responsible for the Ark's internal file layout.

See [Browser download capture](../20-Administration/BrowserCapture.md).

## 7. Recovery preserves intent across two replaceable halves

The design treats the system medium and content medium as separately replaceable. Public configuration mirrors, source checkpoints, software-baseline information and content profiles accompany the recovery tools. A populated content drive and a configuration-only seed are both meaningful inputs.

The stock-Pi setup path turns a supported running Debian-based Pi into an Ark through explicit setup steps rather than requiring a clone of the original system image. Device-specific private identity is separate from the portable public description.

**Why it matters:** the desired end state is understandable and reproducible, rather than existing only as the accidental contents of one working machine.

A [clean generic ARM64 software-phase test](../20-Administration/CleanBootstrapTest.md) has now exercised fresh package, Python and service installation, finding and correcting bootstrap defects. It omits physical radio setup and is distinct from complete Pi acceptance.

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

## Maintaining this chapter

Keep this document focused on implemented mechanisms and the design reasoning behind them. Add source-specific contracts and operational instructions to the linked developer/admin guides. Record acceptance results in the validation documentation. The companion feature catalogue remains the account of what these mechanisms let people do.
