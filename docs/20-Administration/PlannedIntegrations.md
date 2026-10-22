# Integration status

Implemented: household SMB, mounted local file/directory and HTTP-file snapshots; private SMB credentials; per-source readiness; independent normal maintenance and bugout policies; optional OpenPGP; authenticated HA triggers/cancellation and a retrying event outbox. Normal maintenance can be manual, scheduled, or refreshed on reconnection. Bugout has a time budget and optional background handoff on cancellation. See [Household Bugout Backups](Bugout.md).

Manuals is configured at `//192.168.40.127/Manuals` for daily prefetch and refresh at bugout. Verified on 2026-10-21: private credentials are installed, the household worker is running, and scheduled snapshots completed October 20 and 21. All 89 regular-file members of the latest snapshot were read successfully; three samples were restored into temporary storage with matching SHA-256 hashes. Independent source-to-restore comparison remains pending.

Nested resource sections are implemented in the central manifest. They are a display index, not implicit backup jobs or synchronization rules; see [Manifest](Manifest.md). Existing reference-library updates remain with the separate content update worker and are excluded from bugout unless explicitly configured as household tasks.

Still pending: HA connection credentials and package installation, live source/encryption/HA acceptance tests, UPS/power-budget telemetry, application-specific quiesce/export hooks, removable-media export, hardware/GPIO triggers, shutdown/eject policy and retention policy. No door, light or other physical-device actions are configured automatically.


## Library selection workflow

Requested on October 22, 2026: keep the landing page focused on verified local collections. Add a separate Manage library view listing available collections with language, coverage, release date, download size, and installation status, with explicit download actions. A completed download must be registered, verified, activated in its reader, and then represented on the landing page automatically. Candidate collections include English Project Gutenberg books and suitable OpenStreetMap-derived offline map packages; neither is currently installed as a collection. The existing Massachusetts map references remain available separately. The selection/download management screen is planned, not yet implemented.

## Manage Library implementation

The local `/library.html` page now lists installed assets, pending archives, free storage and full updater activity. The curated publisher check offers English Project Gutenberg release/size metadata. OpenStreetMap and USA.gov remain clearly marked references, not installed collections. OSM region/package/reader selection is still planned.

Downloads require the existing network administration password and the fixed-scope helper installed with `sudo venv/bin/python deploy/install_library.py` after administrator approval. It accepts only the curated collection ID and displayed release/size, rechecks publisher metadata and disk space under the worker lock, and passes installation to the existing checksum/activation worker. No arbitrary download URLs or filesystem paths are accepted. The installer grants admin passwordless execution of this helper only, with no command-line arguments. Without this helper the page remains read-only and says setup is required.

### Content removal authorization

Removing installed content must require the same Ark administration password as downloads, plus explicit confirmation identifying the collection to be removed. Browsing remains public. No removal endpoint or delete control currently exists; the download helper does not accept removal actions. Automatic replacement of a verified archive by the existing updater remains part of the update transaction.

### Removal and reinstatement implemented

Manage Library is linked from the System status pop-up. Installed registered files have a Remove action: the confirmation names the item and its size and requires the shared caretaker password. Removal retains source metadata, marks the asset removed, disables its automatic updates, refreshes Kiwix and the published catalogue, then frees the file only after successful publication. A durable journal rolls back an interrupted uncommitted removal before the updater runs. Removed archives appear under Not installed with a password-protected Reinstate action that uses their original supported Kiwix series, verifies the downloaded release, and re-enables updates. This applies to pre-seeded archives too. Utilities without an automatic adapter retain their original package link for manual restoration. Removal acts on the registered file, not unrelated files or whole directories.

Public collection requests and storage-based approval policy remain planned; downloads and reinstatement currently require the caretaker password.
