# Software updates and maintenance

[Check for updates](/config/updates.html) is available from Help. It reads official Pharos software releases on GitHub when requested. Anyone can inspect availability; no caretaker password is needed to read version information. Checks are cached for one minute, do not execute downloaded code, and do not install or download a kit. Preview releases are opt-in. Documentation releases are excluded.

The installed build revision, branch and local publication time identify the running software. The checker compares published source revisions using local Git history when possible. A development build containing a published release is reported as ahead, not offered the old kit as an upgrade. Missing Git history or incomparable revisions produce an explicit comparison warning. An unavailable check never means “up to date.” The last successful result can be retained within the running service; restarting the service clears that cache.

## Three distinct updates

- **Ark software:** dashboard, API, maintenance tools, service definitions and bundled documentation. Configuration migrations may be needed.
- **Library content:** publisher editions, collections and map packages. Manage Library owns these schedules and downloads, independently of software releases.
- **Operating system:** Debian packages, security patches, kernel, firmware and drivers. These have their own package sources, compatibility checks and restart requirements.

The current public archive is a bootstrap/recovery kit, not an in-place update package. Running its provisioning script against a working Ark is not the software update workflow. No automatic software installer is exposed by the checker.

## In-place update contract

A future caretaker-authorized software update must implement this sequence:

- Select an immutable release and channel, with an explicit platform profile and supported configuration/schema range. Verify its manifest and package digest against trusted release metadata; reject an incompatible platform, unsafe downgrade or edited deployment requiring review.
- Check space, active downloads/restoration, bug-out activity and available access paths. Stage the complete package before changing the running system. Offline installation from an already acquired, verified package should use the same validation path.
- Snapshot the installed software and back up mutable state before migrations. Preserve content selection and files, public and private configuration, community posts and banner, usage history, caretaker credentials, TLS/clone identity, network profiles and adapter assignments. Never copy the publisher's identity or credentials over the device's own.
- Show the version, changes and expected interruption, then request caretaker authorization on demand. Apply only explicit, versioned, repeatable migrations and allow a controlled service restart; reboot only when required and disclosed.
- Verify API, dashboard, content readers, storage and network reachability after installation. Commit the new version only after health checks pass. On failure, restore compatible software and state, record diagnostics, and expose recovery instructions. Database migrations need an actual restore path, not merely an old executable.
- Record installed version, date, outcome and rollback result; notify Home Assistant through the existing integration event path. Keep a local readable history.

The bootstrap/recovery configuration and release builder provide inputs to this process. They do not establish its rollback and migration guarantees. The installation operation should be added only with tests for interrupted staging, failed migrations, failed health checks, retained state, offline packages and rollback on spare media.

## Bluetooth

The reference Raspberry Pi 4 has Bluetooth hardware. The current Ark's controller and Bluetooth service have been detected; its radio is powered off and undiscoverable. Practical uses include keyboards, mice, audio devices and specialized serial peripherals. Radio presence does not establish that every peripheral profile works. Power it on and pair devices on demand through operating-system controls; keep discovery and automatic pairing off during ordinary operation. Bluetooth is not currently an Ark content-serving transport or a dashboard-managed feature.
