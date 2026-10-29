# Set up a stock Pi and prepare another Ark drive

**Restoration update:** Optional content now requires a capacity-checked preset and explicit queue approval. The legacy `content_profile.py restore --apply` path is disabled. Fresh bootstrap does not start optional downloads or automatic download timers. See [Restore presets and queue](../20-Administration/RecoveryQueue.md). Spare-media acceptance remains pending.

## Current status and supported starting point

An experimental stock-Pi coordinator and drive-preparation tool are implemented. Their validation, extraction, journal/resume and public-copy behavior are tested. They have **not** been applied to a fresh spare Pi; client/media acceptance is still required. The current running Ark is explicitly refused as an installation target.

The first target is Raspberry Pi OS 64-bit based on Debian 13 (Trixie), on a Pi with aarch64 userspace, primary account `admin` at UID 1000, and NetworkManager. Configure that account in Raspberry Pi Imager; choose your own Linux password. A different account/UID or older OS is not silently converted. Use a local terminal, `wlan0` for the open DataArk hotspot, and Ethernet or a previously configured second Wi-Fi adapter for upstream internet. Existing portal helpers require the reviewed 192.168.4.1/24 layout. This is a declared target baseline, not a fresh-image certification.

The core setup installs library, network/portal, protected management, diagnostics and public file services. VNC, browser terminal, AnyDesk and graphical IDEs are separate optional installations; a stock setup does not claim to duplicate every incidental workstation tool on the source Ark.

Initial software setup needs internet for signed distribution packages, pinned Python requirements and the pinned Kiwix image. A populated library does not by itself make this a fully offline software installer. The PMTiles ARM64 CLI and its license are carried in the kit, so configuration-only media can rebuild the configured regional extract.

## Run the kit from a content drive

The drive carries `START-ARK.txt`, `START-ARK.html`, `START-ARK.sh`, `DATA-ARK-CONFIG` and `DATA-ARK-RECOVERY`. Mount it normally and open START-ARK. From a terminal in that drive's top directory:

```sh
sudo bash START-ARK.sh
sudo bash START-ARK.sh --apply
```

The first command only previews. The second checks the target and asks for `INSTALL` before making the described changes. Review/edit `DATA-ARK-RECOVERY/site.json` for the permitted settings: SSID, country, hostname policy, FTP and other base-device settings; optional restoration and download timers are separately gated. Core layout constraints remain fixed until separately supported. There are no credentials in this JSON. The helper installer privately prompts for a new management password; do not reuse the source Ark's credentials.

Stages: distribution packages; checksum-verified public source; existing content-volume mount; Python environment and PMTiles CLI; API/Apache/Kiwix and protected helpers; hotspot/portal/public content access; missing library content; timers and service checks. The source archive is expanded with traversal/link/special-file checks. A local Git repository is initialized so the new Ark can checkpoint and prepare another kit without a GitHub account. It does not automatically push to GitHub.

The selected content filesystem must already be exFAT or ext4, separate from the boot filesystem, with admin ownership. No formatting or partitioning exists in the coordinator. It attaches the already mounted volume at `/mnt/storage`, records its UUID in fstab and preserves the original mount during setup. Conflicting mounts/fstab entries are refused. Newly prepared replica media have the expected public ownership. A previously prepared drive with different ownership needs its mount options reviewed.

A hostname based on the new machine ID is generated when `hostname` is `auto`; clones do not inherit one machine's hostname. The hotspot's local `dataark` address remains supplied by the portal. `wlan0` becomes an open local-library hotspot; this changes its current connection. An upstream route through Ethernet or another adapter is required beforehand, and SSH-driven application is refused. Do this from a local console so you retain access.

The root-only journal `/var/lib/dataark/bootstrap.json` records completed and interrupted phases and a site-configuration fingerprint. Rerun the same command with the same settings after fixing an interruption. Completed phases are skipped. Source markers, a container label and a recorded AP UUID distinguish this install's partially created resources from unmanaged resources. It refuses another existing Ark or unowned source/container/AP configuration. Phase-specific underlying installers retain their backups; this is not a universal automatic rollback of package installations.

## Populated or configuration-only

Existing complete collections are reused. Missing selected ZIMs/direct maps download with recorded verification; missing collection groups run their source/generator recipes. Saved desired selections are retained even when the content drive has no library payload. The source URLs must remain available. Reference updates and changed rolling datasets retain the limits in [Content restoration](../20-Administration/ContentRestoration.md).

A configuration-only kit may need hundreds of gigabytes and a long download. It is not evidence that the selected publishers are currently reachable. A populated kit can serve its existing content after software setup, but still needs fresh-system reader/client acceptance.

## Prepare another drive

Open **Manage Library > Clone a content drive** to preview configuration-only, whole-collections-that-fit, or all-public-content cloning. See the [drive-cloning guide](../20-Administration/CloneDrive.md) for destination checks, priorities, checksums and resuming interrupted copies.

The kit exports the current public configuration and uses committed Git source. Make a Git checkpoint of intended software changes first. No credentials, hardware identity, private backups or boot OS image are copied. Optional content downloads remain a separate explicit restoration choice.

## Remaining acceptance test

Use spare media and a supported stock Pi. Test both populated and configuration-only kits. Interrupt/resume setup and a drive copy, reboot, and verify the UUID mount, actual Kiwix article/image, maps, PDF/radio tools, captive portal, management password, offline behavior and public/private file boundaries from a separate client. Then use that newly built Ark to prepare a third kit. Only after these tests should the coordinator be described as a supported reproduction process.
