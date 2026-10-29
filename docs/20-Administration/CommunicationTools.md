# Communication and accessibility tools

The **DEJ Software** landing-page card opens local Communicate, the Communicate Keyboard Android installer, and a downloadable Data Ark bootstrap kit. The software files are normal configured content, available locally while connected to the Ark.

Communicate is the publisher’s released browser app, with its application, service worker, manifest and complete icon/artwork set preserved unchanged. It loads from `/library-files/communication/communicate/` while connected to the Ark, including when the Ark has no internet. Text-to-speech runs on the client device and requires an installed offline voice. The Ark cannot supply an offline voice to every client automatically. Plain HTTP may block service-worker installation, clipboard/transfer features or keeping the app after leaving the Ark; optional trusted HTTPS can enable browser capabilities. Saved messages and settings belong to each browser origin and do not migrate automatically from the public website.

The preserved Android APK is published development build **0.2.1-dev.13**, package `com.dej.communicate.keyboard`, minimum Android 8.0. It is clearly labeled as a development build. Its signing identity differs from Play releases; Android will not install it over an existing Play-signed package. Original developer notices and APK signatures are retained. Downloading does not install it automatically.

`deploy/reference/communication.json` is the readable, pinned source recipe: collection links and registered assets, public source URLs, exact sizes and SHA-256 hashes for all twelve publisher files, web build identity, Android version and signing-certificate fingerprint, and the public bootstrap release record. It contains no signing keys or credentials. To reinstall, run `sudo python3 /opt/dataark/tools/install_communication.py`. Verified existing files are reused; checksum mismatches retain the working copy until a verified replacement is ready. Upstream changes require reviewing and updating this pin; there is no silent software update.

## Download the Ark kit

Choose **Ark bootstrap kit & setup** on the DEJ Software card, or open `/library-files/communication/index.html#bootstrap`. The download, release details and checksum file are served from the content drive under `communication/ark-bootstrap/`; obtaining them needs no upstream internet. The pinned preview release is about 40.2 MiB (42.1 MB).

This is the published, public configuration/software seed. It is distinct from making a fresh clone of this Ark’s current selections with [Clone a content drive](CloneDrive.md). Extract it onto a prepared content drive and follow its README and the [installation guide](../30-Developer/StockPiSetup.md). It contains no library payloads or machine credentials. New-Pi setup still needs internet for system/software dependencies, and content restoration is a separate choice.

The kit asset has a `source_check_url` pointing to the publisher’s lightweight release notice. Normal weekly reference checks flag changes there without repeatedly downloading the archive. A changed notice is a review signal: update the pinned version, URL, size and hash in the readable recipe before installing a new release. It does not silently replace software. The package hash remains separate from the release-notice fingerprint.

The communication recipe is included in content export and the Minimal recovery preset. It verifies supporting web assets as well as all three primary catalogue entries; restoring only the HTML would be insufficient. Complete-collection cloning includes the kit too. The source recipe and installer travel in recovery checkpoints. Spare-media acceptance remains outstanding for recovery as a whole.
