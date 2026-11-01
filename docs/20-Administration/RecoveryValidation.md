# Recovery validation — 25 October 2026

## Verified on the running Ark, using isolated test data

42 tests passed: community storage/API and restore (30), stock-Pi setup and content-profile reconstruction (12).

The board drill created a conversation, reply and colored Markdown banner, took a backup, replaced the test data, restored the backup and checked the reply and banner. Original author deletion codes still work for both posts and replies. A second restore from the automatic pre-restore snapshot successfully returned to the newer conversation and banner; that conversation's deletion code also still worked. No live community messages or banner were replaced.

Failure checks cover invalid databases, unsafe schema, changed data after preview, expired/wrong-device previews, unavailable snapshot storage and transaction failure. Restoration either fails without replacing the live data or reports a committed success separately from a later cleanup warning.

## Portable kit verification

The current content-drive kit passed its source, bootstrap and PMTiles checksum checks in the stock-Pi coordinator's preview. Its only reported blockers were expected protections against applying a fresh installation over this existing Ark: existing service, existing checkout and occupied ports. No installer phases were applied.

The setup tests cover supported configuration, safe extraction, interrupted phase resume, public-content copying and refusal to use live media as a replica destination. Content-profile tests cover selection preservation and verified download behavior.

## Still requires spare hardware/media

This is not a fresh-Pi certification. No replacement boot card was flashed, no content drive was emptied, no reboot or network change was performed. Initial packages, Python dependencies and the Kiwix container still require internet; an offline software cache has not been completed.

Use the procedure in [Stock-Pi setup](../30-Developer/StockPiSetup.md) on a spare supported Raspberry Pi OS 64-bit / Debian 13 installation, with admin UID 1000 and a separate content volume. Test populated and configuration-only media, interruption/resume, reboot, portal access, real offline content, management authentication and preparation of another kit. See [paired-media recovery](PairedRecovery.md).


## Chained acceptance: rebuilt Ark, then empty content media

The successful populated-media/new-system test should leave a functioning Ark. Preserve that recovered system as the starting point for the next test: replace its content medium with a separate empty, prepared volume and rebuild from the surviving system's saved configuration. This tests the other half of recovery without rebuilding the operating system again.

This is the **empty-media scenario**, distinct from a configuration-only seed drive: the replacement contains neither content nor an Ark configuration kit. The surviving system must supply the desired selection and recovery tools. A fresh system plus completely empty media is not the same test.

### Before the swap

1. Complete the preceding test's real-client, offline and reboot checks. Record the source revision and the chosen restoration preset; keep the original media available for rollback.
2. Quiesce downloads, restoration and household jobs. Verify that the recovered system holds a valid desired-content profile independently of the content drive. Record its checksum, selected package IDs, disabled selections, source information and personalization. A passing preceding test must not merely leave these on the drive about to be removed.
3. Save the evidence and protected appliance settings outside the replacement volume. Identify the spare volume explicitly by stable device identity, capacity and filesystem. No test step formats or empties the original collection.
4. Shut down cleanly and swap only the content medium. Use a separately prepared empty supported filesystem at the expected mount point; device preparation is an explicit operator step.

### Rebuild and observe

1. Boot with the replacement volume. Verify that the saved desired selection has not been replaced by an empty inventory, and that no optional download or formatting has started automatically.
2. Confirm basic dashboard, terminal and caretaker access. Missing content should be reported honestly; it must not be presented as readable merely because it remains configured.
3. Preview the restoration presets against the new volume. Check dependencies, source identities, temporary space, headroom and reserve. Approve the exact reviewed plan using the [restoration queue workflow](RecoveryQueue.md). Use a capacity-appropriate preset; a partial preset is not evidence that Full has passed.
4. Run restoration with upstream connectivity. Record queue transitions, per-package outcomes, verification and activation. Where practical, pause and resume a small package before attempting an interruption drill; perform the interruption drill on spare media only.
5. Verify real restored files through their intended readers and distribution paths, including an article with images, a PDF and a map when included by the approved preset. Check that installed material appears on the landing page and that intentionally excluded packages remain excluded.
6. Isolate upstream access and repeat the local client checks. Reboot and verify that the mount, services, installed selection and queue state return correctly.
7. Prepare a new public configuration mirror and recovery source checkpoint on the rebuilt content drive. Verify their revision and checksums. The rebuilt half should now carry the information needed for a subsequent replacement-system test, without copying private machine identity into a public kit.

### Record the result

Record both tests separately, including hardware/media identities, source revision, profile checksum, preset, restored package IDs, bytes, timings, failures, interruption behavior and client checks. Compare the before/after desired selections and explain any intentional differences. Retain rollback media until review is complete.

**Status:** this is the next acceptance procedure, not a completed test. The desktop emulator's read-only production-media mount cannot establish empty-media or physical spare-system acceptance. Do not merge the recovery branch or call two-way regeneration dependable on the strength of this procedure alone.


## 28 October 2026: ARM64 empty-filesystem drill

**Result: passed within the software-only scope below. Physical paired-media acceptance remains pending.**

The running generic Debian ARM64 emulator was used as the surviving system. A new, exclusively created 16 GiB sparse image was formatted as ext4 and mounted separately at `/var/tmp/ark-empty-media-drill-20261028/media`. The production `/mnt/storage` share remained read-only; neither physical medium was swapped, formatted or overwritten.

The drill used a deliberately small saved profile, held outside the replacement filesystem, with two enabled PDF targets and one disabled target. Both enabled targets retrieved the public IRS W-9 PDF over HTTPS (140,815 bytes, SHA-256 `2d420cbb4123dcf1fb82595b2359cfbb5d81f00b9df9d359fcc7af361d093f53`). This exercised the real queue subprocess, type handler, downloader and checksum verification. It did not restore the full appliance profile or run collection/index recipes.

Verified:

- The new mounted filesystem initially contained no content or configuration kit.
- Capacity planning included the 10 GiB reserve, and queue creation used the exact reviewed plan identity.
- The first package completed, then the queue paused before the second.
- The second package resumed with a 1,024-byte staged partial file.
- The completed first package was not rerun; both jobs completed in one attempt each.
- Both final PDF hashes matched the baseline, the disabled target stayed absent and the saved profile checksum stayed unchanged.
- Unmounting and remounting the new filesystem retained both verified files.
- The emulator dashboard still returned HTTP 200 and its production-media CIFS mount remained read-only.

Separately, **34 stock-setup, content-profile and restoration-queue regression tests passed** inside the ARM64 guest with local-caretaker privilege and disk-backed temporary storage. Initial unprivileged execution correctly met the worker privilege boundary. A subsequent run in RAM-backed `/tmp` failed two reserve checks; using `TMPDIR=/var/tmp` supplied the disk capacity required by those fixtures. Production reserve policy was not reduced or bypassed.

Evidence retained in the guest: `/var/tmp/ark-empty-media-drill-20261028/result.json`, its queue state and worker log, and `/var/tmp/ark-recovery-regression-disk.log`. The disposable filesystem remains mounted separately for inspection; it is not configured as the Ark's content mount or a boot-time mount.

Still untested by this drill: fresh stock-Pi installation, replacement of physical content media, the complete saved selection, collection-reader/index activation, real-client offline viewing, reboot/power-interruption recovery on replacement media, and regeneration of a complete kit from that rebuilt appliance. The two-test physical acceptance chain above is therefore **not complete**. No recovery merge or dependable-regeneration claim follows from these results.


## Clean-OS bootstrap test

The clean Debian ARM64 software-phase test is documented separately in [Clean-OS software bootstrap acceptance](CleanBootstrapTest.md). The clean software phases passed after fixes and recorded retries, with two guest reboots and 43 relevant regressions passing. A subsequent [uninterrupted frozen-kit replay](FrozenBootstrapReplay.md) also passed, including 43 regressions and reboot/service checks. Physical network setup and spare-media acceptance remain untested. Its phase journal and outcome must be reviewed independently of the earlier empty-volume drill; that drill began with an already configured Ark.


## 29 October 2026: physical spare-drive Minimal content proof

**Passed:** the existing Ark supplied the Minimal payload to an empty 474.9 GiB NTFS partition on the separate Toshiba USB drive (filesystem UUID `5A5A5A1A5A59F2ED`). The original OfflineRepo volume remained mounted and the active configuration stayed unchanged.

The proof copied and SHA-256 verified 39 files, totaling 17,060,358 bytes: the three selected preparedness PDFs, radio-study pools and diagrams, and Communicate/Communicate Keyboard support files. The five registered payload restore handlers then reused these files successfully inside a private network namespace with no external network access. No content was downloaded. Portable catalogues were generated from the spare's actual files; the spare was unmounted and remounted, every copied hash was rechecked, and seven representative HTTP reads passed, including all three PDFs.

The filesystem also passed staged writing, file and directory fsync, permissions requests, atomic replacement and clean unmount/remount. This is a physical content-copy/reuse proof, separate from the native restoration-queue, live-content-volume swap and clean-OS bootstrap tests. Evidence is retained on the boot card under `/var/lib/dataark/acceptance/physical-spare-20261029/`, including `minimal-proof-result.json` and `copied-minimal.json`.


## Acceptance cases: content drive absent or lost

These cases test the system half independently of a usable content drive. A missing drive is distinct from an attached empty drive. Record each result separately; a clean installation or successful empty-drive restore does not establish these cases.

### A. No content drive has ever been attached

Use a spare system card with the appliance software and its system-side configuration, but no content volume. Boot with Ethernet and, where configured, the hotspot available.

- Boot reaches a usable system without an indefinite mount wait. Dashboard, Help, status and caretaker recovery access remain reachable.
- Status explicitly reports **Content drive not connected**; it does not show healthy/green, an empty installed library, zero-capacity storage, or the system card's capacity as content capacity.
- Configured source references remain discoverable; offline files and readers are not advertised as available.
- The desired selection and source definitions remain intact. No automatic formatting, initialization, reinstatement or download starts.
- Content writes, queue activation and content removal refuse the absent mount. Nothing falls through into the bare mount directory on the system card. Record mount-directory contents and system-card free space before and after.
- Connecting the intended volume, then using the documented mount/recovery action, restores its catalogue without replacing the saved selection. A different volume requires an explicit reviewed action.
- Home Assistant receives the missing-storage condition and its resolution when configured.

### B. A connected content drive disappears during operation

Use disposable test media or an isolated fault-injection fixture. Do not pull the original library drive to simulate a fault. Exercise loss while idle, while reading, and during a small staged write/update; retain checksums and the pre-test configuration.

- Within a bounded status-check interval, the dashboard changes from healthy to an explicit missing/disconnected or I/O-error state. Previously cached green state must not mask the failure.
- Dashboard, Help, network access, caretaker controls and system-side diagnostics remain usable. Reader/file requests fail clearly and promptly rather than hanging indefinitely or serving a misleading success page.
- In-flight work fails or pauses with a recorded reason. It does not mark partial files verified, activate an incomplete edition, erase the desired selection, or repeatedly fill the system card.
- Verify both a genuinely absent mount and a mount that remains listed but returns I/O errors; a mount-point check alone is not sufficient for the latter.
- Reconnect the same media and follow the documented recovery action. Recheck filesystem health, retained file hashes, reader operation and queue state. Healthy status returns only after fresh successful checks.
- Retry/resume preserves the last verified copy and requires normal caretaker approval where applicable. Repeat a reboot after recovery.
- Home Assistant receives the storage-loss and recovery events when configured; local diagnostic evidence survives the missing drive.

**Evidence:** record boot duration, detection/recovery times, status transitions, HTTP outcomes, system-card usage, mount identities, file hashes, queue/journal records and Home Assistant results. The automated resource/health regressions cover detection and recovery of an absent mount; they do not establish boot, hot-unplug, I/O-fault or complete writer protection acceptance.


### 31 October 2026: live unmounted-media check

On the restored physical Pi, both the 1 TB exFAT content volume and the separate NTFS spare volume were cleanly unmounted. The Kiwix reader and the usage/community-backup timers were paused for the operation; no forced removal or in-flight writer fault was used.

Dashboard, status API, Help, Manage Library and the community page returned HTTP 200 with both volumes absent. Status changed to degraded and reported SSD storage unavailable and Kiwix unavailable. Content-storage capacity was unknown rather than falling back to the system card. The bare content mount directory remained empty, and the system-side desired-selection checksum was unchanged.

Both volumes were remounted and services/timers restored. The spare's desktop-managed mount directory had been removed automatically during unmount; recreating it allowed the same volume UUID to be remounted without filesystem repair. The reader returned HTTP 200 and health returned to OK with no problems.

This establishes graceful live operation and reconnection for a clean unmount. It does not establish cold boot without a drive, never-attached demonstration provisioning, sudden I/O failure, or interruption of an active write. Evidence: `/var/lib/dataark/acceptance/no-content-drive-20261031/result.json` on the test system.


### 31 October 2026: capped demo-library component acceptance

In a private mount namespace on the test Pi, the demo-storage component allocated and mounted a real 2 GiB ext4 image on the system card. A write exceeding the image capacity failed with ENOSPC, did not grow the backing image, and consumed no additional system-card space. Repeated setup reused the same image without formatting it again. The official 100-article Wikipedia sample passed its pinned size and checksum, both bundled catalogue PDFs were copied, and the samples survived unmount/remount.

The live content SSD remained mounted in the host namespace and the API remained active. Thirty-six allocation, installer, platform and reader tests passed, including capacity/headroom checks, refusal to replace existing drives or mount entries, preservation of original source definitions, and interruption/symlink guards. Evidence: `/var/lib/dataark/acceptance/demo-library-20261031/result.json` on the test Pi.

This component test is separate from a complete fresh-system installation with the demo option, reboot, browser-reader and client checks. Those form the card-only demonstration acceptance case; they are not established merely by successful loop-volume creation.


### 31 October 2026: physical spare-boot-card software recovery

A newly imaged Raspberry Pi OS 64-bit Debian 13 card booted the reference Pi with admin UID 1000 and no Ark software installed. The existing content drive supplied the source/configuration kit. Recovery completed all ten phases and the rebuilt appliance rebooted with its content mount, Ethernet, hotspot, web/API, Kiwix, SMB and FTP services active. All eight archive entry pages and representative PDFs returned HTTP 200; health reported OK with no problems. Windows LAN checks also passed.

The run required recorded corrections: a longer bounded cold-reader startup wait, explicit guarded Ethernet resume, exclusion of transient Docker links from physical-network identity, and consistent local/cloud-init hostname ownership. It is a resumed recovery with documented fixes, not an uninterrupted replay of the published kit. The original system card was retained. Physical client/offline and the complete paired-media sequence remain separate acceptance cases.

Evidence on the test system: `/var/lib/dataark/acceptance/physical-boot-card-20261031/`. Copies of the pre-swap and post-reboot results were also retained outside both test media.
