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
