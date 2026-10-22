# Integration status

Implemented: household SMB, mounted local file/directory and HTTP-file snapshots; private SMB credentials; per-source readiness; independent normal maintenance and bugout policies; optional OpenPGP; authenticated HA triggers/cancellation and a retrying event outbox. Normal maintenance can be manual, scheduled, or refreshed on reconnection. Bugout has a time budget and optional background handoff on cancellation. See [Household Bugout Backups](Bugout.md).

Manuals is configured at `//192.168.40.127/Manuals` for daily prefetch and refresh at bugout. Verified on 2026-10-21: private credentials are installed, the household worker is running, and scheduled snapshots completed October 20 and 21. All 89 regular-file members of the latest snapshot were read successfully; three samples were restored into temporary storage with matching SHA-256 hashes. Independent source-to-restore comparison remains pending.

Nested resource sections are implemented in the central manifest. They are a display index, not implicit backup jobs or synchronization rules; see [Manifest](Manifest.md). Existing reference-library updates remain with the separate content update worker and are excluded from bugout unless explicitly configured as household tasks.

Still pending: HA connection credentials and package installation, live source/encryption/HA acceptance tests, UPS/power-budget telemetry, application-specific quiesce/export hooks, removable-media export, hardware/GPIO triggers, shutdown/eject policy and retention policy. No door, light or other physical-device actions are configured automatically.


## Library management status

Implemented October 22, 2026: Manage Library in the System pop-up; installed/pending/removed inventory; free-space and full updater status; curated English Gutenberg download requests; password-protected removal and reinstatement; retained sources for pre-seeded archives; page-memory caretaker authentication; lifecycle diagnostics; and anonymous read-only FTP. See [Library management](Library.md) for current behavior.

Still planned: public collection requests and storage-sensitive caretaker approval, OpenStreetMap region/package/reader selection, and a browser viewer for specialized GIS datasets. Utilities without an automatic adapter retain a source link for manual restoration. The existence of a reference link does not establish offline installation.
