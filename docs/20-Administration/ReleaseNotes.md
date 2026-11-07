# Current implementation notes

Reviewed November 6, 2026. These notes describe the documented software. Use the **System** tab or `/assets/build-info.json` to identify an individual Ark's installed revision and publication time; an older installed edition may differ.

- The original Raspberry Pi flavor provides a local hotspot; the LAN-server and container forms serve an existing local network, wired or Wi-Fi as provided by the host. Public reading does not require a caretaker account.
- Public configuration is split into `ark.yaml`, collection definitions, catalogues and generated version/order snapshots. The folder-based editor supports syntax coloring, section navigation, search, validation, History and unsaved-change detection. Reading configuration does not prompt for a password.
- Caretaker authorization is requested on demand. An optional 1–120 minute cache has a fixed expiry. **Lock now** clears remembered access in all open tabs at the same Ark address in this browser; it does not send passwords between tabs or devices. The floating unlocked padlock shows the remaining minutes.
- System details use System, Library and Usage tabs. Manage Library is on Library; system administration actions are on System. Network and display controls use slider switches. Help and Developer API open directly.
- First-owner setup uses the supplied four-digit code and separately selected caretaker and Linux-admin passwords. Public browsing remains available without completing setup. The code prevents nearby setup-time hijacking; root login remains disabled.
- Help provides release checks, signed software-package verification and authorized installation. Downloads, installation, restart, health checks and rollback have separate states. Bootstrap kits, content updates and operating-system packages have distinct workflows.
- Adding an empty external drive offers to copy and verify existing content before switching. Usable installed editions are reused without redownloading; publisher checks and missing-content restoration can follow separately.
- Source issues distinguish publisher changes, failed checks and scheduled browser review. Individual warning snoozes leave retries enabled, preserve installed content and expire automatically. A failed recovery-profile export rolls back the source-policy change and reports its cause.
- Generated recovery snapshots are temporary projections of saved public configuration. They do not overwrite editable projects or allow stale generated files to block later exports and restoration-plan checks.
- The banner supports Markdown, date/greeting variables, appearance controls and optional broadcast to open clients. The community board supports nested replies, author removal links, caretaker editing and backup/restore.
- Home Assistant can consume health, bug-out and collection/configuration events. Delivery requires configuration on that individual Ark; notifications and physical-device actions require the household's chosen automations.
- File distribution includes HTTP, read-only SMB and anonymous read-only FTP. SSH/SFTP, rsync and the browser terminal use their own account authorization.

## Tested scope and operating limits

Physical clean-install, sample-library transfer, reboot and retained-recipient software-upgrade results are recorded in [Release validation](ReleaseAudit.md) and [Recovery validation](RecoveryValidation.md). A successful sample test is not a complete-library restoration or a qualification of every storage device. [System-card recovery](SystemCardRecovery.md) covers preserving and repairing a damaged operating-system card independently of the content drive.

Specialized GIS datasets may require an external viewer; street-map search and routing are not provided. Public collection suggestions, complete offline provisioning caches, household-specific automation/encryption acceptance, and UPS/shutdown policies retain their separate scope. See [Acceptance tests](AcceptanceTests.md), [Recovery queue](RecoveryQueue.md) and [Home Assistant](HomeAssistant.md).
