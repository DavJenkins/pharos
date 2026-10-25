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
