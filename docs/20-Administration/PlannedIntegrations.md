# Integration status

Implemented: household SMB, mounted local file/directory and HTTP-file snapshots; private SMB credentials; per-source readiness; independent normal maintenance and bugout policies; optional OpenPGP; authenticated HA triggers/cancellation and a retrying event outbox. Normal maintenance can be manual, scheduled, or refreshed on reconnection. Bugout has a time budget and optional background handoff on cancellation. See [Household Bugout Backups](Bugout.md).

Manuals is configured at `//192.168.40.127/Manuals` for daily prefetch and refresh at bugout. Its private credentials still need to be supplied on the Ark. The worker was previously installed; updated code needs deployment and worker restart.

Nested resource sections are implemented in the central manifest. They are a display index, not implicit backup jobs or synchronization rules; see [Manifest](Manifest.md). Existing reference-library updates remain with the separate content update worker and are excluded from bugout unless explicitly configured as household tasks.

Still pending: HA connection credentials and package installation, live source/encryption/HA acceptance tests, UPS/power-budget telemetry, application-specific quiesce/export hooks, removable-media export, hardware/GPIO triggers, shutdown/eject policy and retention policy. No door, light or other physical-device actions are configured automatically.
