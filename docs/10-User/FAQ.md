# Frequently asked questions

## Does Data Ark need the internet?

Installed local content does not. Downloading new collections, checking publishers, and following online links do. Your phone may use cellular data independently, which can obscure an offline test.

## Why does my phone say Sign in to network?

The Ark uses captive-portal discovery to guide devices to its landing page. Tap the notification or manually open http://192.168.4.1/. No reader account is required. Automatic pop-up behavior depends on the device and may differ when it remembers a previous connection.

## What does Ark offline mean?

The Ark cannot currently confirm an upstream internet connection. The hotspot and local library may still work normally. Ark connection unknown means the status check could not establish a result.

## Why do I have internet on my phone while pass-through is off?

Your phone may be using cellular data. Pass-through refers only to internet routed through the Ark for this hotspot client. It does not control cellular service or other devices.

## Does everyone need a password to read?

No. Reading and copying the public library are open. Changing the library currently requires the shared caretaker password, which is also used for network administration. It is not automatically the Wi-Fi or Pi login password. Passwords are not published in these docs.

## Why did a management action ask for the password again?

Successful authentication is remembered in that page's memory for 15 minutes after the last successful action. Reloading, leaving, locking management, or an authentication rejection clears it. A rejected password explicitly says Password not accepted. The browser does not save this session credential in localStorage or cookies.

## Is Download queued the same as Download complete?

No. Queued means the request was accepted. Downloading transfers the archive; verifying checks its integrity; activating updates the reader and published pages. Only a successfully installed collection should be called complete. Activation can take minutes, particularly for large archives.

## Can I close the window during a download?

Yes, after the request is accepted, the background worker continues. Return to Manage Library for current progress. Interrupted transfers normally resume when the Ark is online again. Do not unplug the SSD.

## Do we need Wikipedia with and without images?

Usually the illustrated edition is sufficient. A smaller text-only copy can be useful for copying to a device with less storage. Different release dates mean the editions are not identical snapshots. Removing one does not remove the other.

## Can removed pre-seeded archives be restored?

Yes, if their supported publisher/source configuration remains registered. Reinstate downloads and verifies an available release; it is not an undo from a local trash bin. Utilities without an automatic download adapter retain their original package link for manual restoration.

## Can I use FTP?

Yes. Anonymous read-only FTP is available on port 21. Use an FTP client with the Ark's address, username anonymous, no password, and passive mode; open the library folder. Uploads, deletion, and private/staging directories are blocked. FTP distributes public files; it is not the administration interface.

## What about SFTP, SMB, and rsync?

SMB offers the read-only Offline-Archives share. SFTP and rsync over SSH use an authorized Pi account and that account's filesystem permissions; they are administrator tools, not anonymous access. The caretaker password is not an SSH account. See the Access your content page for addresses and paths.

## Why will a map or copied archive not open?

A ZIM archive needs Kiwix. A PDF needs a PDF reader. GIS ZIP archives are datasets that require GIS software, not a ready-made interactive browser map. The landing page links to collection indexes, but that does not imply a built-in viewer for every file format.

## Is everything backed up and fully tested?

No. Configuration snapshots, curated content, household backups, and application source have different recovery requirements. A full spare-storage restore and several client/offline acceptance cases remain pending. See the [acceptance tests](../20-Administration/AcceptanceTests.md) for the distinction between implemented features and verified recovery.
