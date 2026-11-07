# Recover a damaged system card

A blank desktop, a cursor without a login prompt, or missing networking can have a common operating-system cause. Check startup logs before assuming a display fault. A working library drive does not replace the system card's operating system, private settings or credentials.

## Preserve before repairing

1. Stop repeated power cycling. Shut down normally if a terminal or remote connection still works; otherwise power off before removing the card.
2. Identify the card by capacity, partition layout and physical-device identity. Do not rely on a desktop drive letter alone. Keep the content drive and any recipient card separate.
3. Read the entire card into a new image without opening the source device for writing. Read the saved image back, compare its SHA-256 with the bytes read from the card, and retain the length, digest and device-identification record.
4. Keep an additional protected copy of appliance configuration, local source changes, release-signing material, account/network settings and community data. These backups are private; they do not belong on the public website or library share.

A verified image preserves the bytes that were read, including any existing damage. It is a recovery resource, not proof that the filesystem or every installed file is healthy. See [Source, backups and handover](SourceAndHandover.md).

## Diagnose offline

Inspect a saved image read-only and avoid journal replay during initial evidence collection. Examine the boot command line, mount configuration, service journal, display-manager log and package records. A clean-looking filesystem flag and available free space do not replace a full filesystem check.

Run filesystem checks on an unmounted filesystem or a separate working image. Never repair a mounted root filesystem. Separate metadata faults, missing files, wrong file bytes, permission errors and legitimate local modifications. Package checksums help identify which installed files differ; configuration files may intentionally differ from publisher defaults.

For a shared-library error, inspect both the symbolic link and its target. Restoring the link alone does not restore a missing library. A single missing dependency can prevent D-Bus, networking and the desktop from starting together.

## Use matching repair sources

The installed package's cached archive is a useful repair source. Another known-working Ark image can also supply a file when its architecture and checksum match the destination's installed package record. Do not mix incompatible library versions or copy a donor's identity, setup code, credentials or personalized configuration.

Test filesystem repair on a separate copy first. A temporary repair program must validate its complete payload and destination conditions before writing, preserve unexpected local files, use the required ownership/modes, verify written bytes and retain a readable result. If repair is staged through a one-time boot action, preserve the original boot command line and restore it before returning to normal boot. Do not leave a recurring recovery command enabled.

Operating-system repair is separate from an [Ark software update](SoftwareUpdates.md). Restoring Debian package files does not install a newer Ark release or prove that every application is current.

## Verify recovery

- Confirm the normal boot configuration has been restored and the device survives its normal startup.
- Check the desktop, SSH, D-Bus, NetworkManager, Ark API, web server and configured readers.
- Verify the selected content filesystem is mounted at the intended location; do not mistake an empty mount-point directory for the library.
- Open the dashboard, Help and representative saved content from a client.
- Check system-unit failures, kernel storage errors and power/undervoltage observations. Distinguish unrelated publisher warnings from operating-system failures.
- Retain the original image and repair record. Investigate unexplained corruption; a successful repair does not certify the card's remaining lifetime.

Full-capacity destructive media tests belong on disposable or already-backed-up media. Repeated successful boots and full-image readback provide useful evidence, but do not replace a complete write/read test or guarantee future reliability.

## November 6, 2026 prototype result

The prototype's original system card had a missing `libsystemd` target, malformed configuration data and filesystem metadata inconsistencies. A verified full-card image and separate protected file archive were retained before repair. Filesystem repair passed on a working metadata image. Package records, a known-working recipient image and exact cached packages supplied 547 checksum-matched file replacements; intentional local modifications were retained.

The one-time repair completed, verified all 547 files, restored the original boot command line and returned to normal startup. Desktop access was confirmed by the operator. SSH, networking, the content-drive mount, dashboard and handbook passed; systemd reported no failed system units and that boot showed no kernel storage or undervoltage errors. Existing publisher-check warnings remained separate. These observations establish recovery of this installation, not a general card-lifetime guarantee.
