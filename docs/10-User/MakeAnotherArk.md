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

The sharing page links to the preparation guide for these formats. It does not yet provide a system-card imaging wizard or generalized recipient preparation. Do not distribute a raw image of a personally configured system card; preserve its public content but remove owner credentials and arrange fresh identities and first-owner setup.

See [ways to build or share an Ark](SharingAnArk.md), [drive cloning](../20-Administration/CloneDrive.md), [restoration](../20-Administration/RecoveryQueue.md) and [external-drive migration](../20-Administration/SystemCardLibrary.md).
