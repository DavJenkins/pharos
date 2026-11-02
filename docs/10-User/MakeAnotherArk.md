# Make another Ark

[Open Make another Ark on this appliance](/make-ark.html).

Open **Help → Make another Ark** or **Manage Library → Make another Ark** on a running appliance. Choose what to give someone before choosing the individual tools.

## A content drive

1. Connect a separate, empty formatted USB drive. Choose **Make a content drive**, then **Find attached drives**. Caretaker authorization is requested on demand; merely opening or refreshing the page does not prompt.
2. Select the destination and choose configuration/software only, whole collections that fit, or all public content.
3. Choose **Review copy plan**. The Ark mounts the selected partition if needed and shows its UUID, included/skipped collections, space requirements and reserve. Nothing is formatted, erased or downloaded.
4. Choose **Start verified copy**. The reviewed plan is checked again before the persistent worker begins. Source or destination changes invalidate approval.
5. Follow progress, or leave and return later. **Pause copy** stops the worker while retaining verified and partial files. To resume, find the same drive, choose the same mode, review again and select **Resume verified copy**.
6. When ready, choose **Safely eject completed drive**. Disconnect only after the unmount succeeds. The drive’s `START-HERE.html` lists verified content; `START-ARK.html` describes installing on the receiving Linux host.

Public software and configuration travel with the drive. Private household backups, passwords, SSH keys and original device identities do not. This drive is not a bootable operating system. Installing the recipient’s software still requires the supported OS and internet for dependencies; copied content does not need another download.

## A downloadable kit

The download choice opens the preserved bootstrap package in the DEJ Software collection. It is the pinned release, not an automatic export of the running appliance. Its version may differ from the installed software. The archive is a software/configuration kit without full library payloads or a preinstalled OS. The local collection must be installed to provide this download offline.

## Restore content on the receiving Ark

Open **Restore Library**. Review a capacity-checked preset and choose **Start this restoration**. This explicitly approves downloads using the Ark’s connection. Unknown sizes and insufficient capacity block starting.

Use **Pause**, **Resume unfinished packages** or **Cancel restoration** from the browser. Verified content and partial downloads are retained. A completed queue needs no resumption. A changed saved profile requires a fresh plan. To start a different selection, first finish or cancel the existing queue, then explicitly select **Keep the finished or cancelled queue in history and start this new selection**. Queue history and logs are preserved under `/var/lib/dataark/recovery-history`.

Progress and controls reflect whether the persistent worker is active. A stopped worker is shown as interrupted rather than permanently running. Restarts do not silently approve a new plan. Requests and outcomes enter the collection lifecycle feed used by Home Assistant.

The original terminal workflows remain under **Terminal alternative** and in the administration guides. Browser controls invoke fixed helpers, not arbitrary commands or paths.

## Ready system cards and complete appliances

Choose **Prepare a system card** to build a downloadable preparation ZIP. Extract it on Windows, Linux or a Pi with a card reader. The package names the exact official Raspberry Pi OS image it accepts; obtain that image separately and install Raspberry Pi Imager. The writer shows the destination's disk identity and requires an exact erase confirmation. It verifies the OS image and copied kit and creates a private printable welcome sheet with a fresh four-digit setup code.

Boot the written card in the receiving Pi with Ethernet and internet. It installs the Ark and the fixed sample library automatically, within the selected storage allocation. Optional large collections are not restored. A successful build prepares first-owner setup and powers off. That is the point at which the card is ready to give away: imaging alone does not produce an installed offline appliance. If interrupted, the persistent build service resumes using the installation journal; inspect the retained logs if it reports failure.

The recipient can then boot offline, join DataArk Wi-Fi, enter the sheet's one-time code and choose separate caretaker and Linux admin passwords. No provisioner SSH key or common root password is carried over. The sheet can be printed or saved as PDF; keep it private.

For an already installed complete appliance, system-card library or LAN server, choose **Prepare an appliance for its new owner**. Inspection explains blockers and the planned changes. Review personal home/browser files and household data before approving: this preserves public content and establishes fresh identities, but is not a secure wipe of arbitrary personal files. Save its private welcome sheet, then shut down. The next boot replaces identities and starts recipient setup. A LAN recipient uses the supplied hostname on the existing network; a hotspot recipient uses the configured hotspot name.

## Install from a kit

Run the drive's `START-ARK.sh` launcher with sudo on a supported Linux installation. It asks for the platform, hotspot details where applicable, and storage choice, shows the discovered plan, and accepts approval in the same session. No command-copy round trip is needed. Its printed explicit command remains available for terminal users. A blocked plan cannot be approved. Saved choices and the installation journal support resumption.

## Adopt or recover library storage

Open **Library storage and recovery** from Manage Library or this sharing page:

- **Reconnect configured library** retries the existing mount without changing the saved selection.
- **Adopt a populated Ark drive** reviews its public profile and configuration differences. Keep the host's desired collection or explicitly use the drive's public collection. Recorded SHA-256 receipts are checked; other files are fingerprinted locally, which does not authenticate them against a publisher. No drive-provided code or private host configuration is installed.
- **Replace missing or unwanted library storage** selects an empty formatted drive while keeping the saved desired collection. If the current library is available, optionally copy it first; the whole copy plus reserve must fit. If it is absent, start with empty storage and choose downloads separately through Restore Library.

Each handover uses a reviewed plan and rechecks source/destination identity before activation. Filesystems are not formatted and original content is retained. An activation failure or interrupted activation restores the previous configuration and mount selection from a private journal. Management remains available when the content drive is absent. An unavailable original drive still needs reconnecting or replacement; rollback cannot manufacture missing hardware.

See [ways to build or share an Ark](SharingAnArk.md), [drive cloning](../20-Administration/CloneDrive.md), [restoration](../20-Administration/RecoveryQueue.md) and [external-drive migration](../20-Administration/SystemCardLibrary.md).
