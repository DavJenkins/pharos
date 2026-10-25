# Paired-media recovery

The target is a working, populated, quiescent Ark that can be separated into two recoverable halves. Give the original boot card a replacement content drive, and give the original content drive a replacement boot card: both resulting appliances should be able to regenerate what they are missing.

## Reciprocal responsibilities

The boot card keeps the authoritative desired-content profile and rebuild tools. The content drive carries readable configuration, a checkpointed source archive and a software-baseline inventory. GitHub and an off-appliance copy provide additional protection; neither original medium should be the only place describing the other.

`config/recovery.yaml` records this design and policies. Automatic rebuild on boot and disk formatting are disabled. A missing or empty drive must never overwrite the saved desired library.

## Present implementation

Content reconstruction on an already configured Ark is implemented by `tools/content_profile.py`, with preview, verification, resumable direct downloads, generator recipes and a public media-drive mirror. See [Content restoration](ContentRestoration.md). A small isolated publisher-file rebuild and regression tests passed; a complete empty-SSD restore has not been performed.

The content drive's `DATA-ARK-RECOVERY` directory contains a Git-checkpointed source archive, its checksum and revision, the public recovery policy and a software-baseline inventory. These files deliberately exclude private credentials and runtime household backups. This makes the source and dependency descriptions available when the original boot card is gone.

The reverse direction now has an experimental stock-Pi coordinator and configuration-only/populated drive-preparation tool. See [stock-Pi setup and replication](../30-Developer/StockPiSetup.md). It is **not ready to claim tested unattended recovery**. A source archive and package list are not a bootable image or an offline package cache. A blank card cannot run its own installer. The remaining boot-card kit needs a verified supported OS image, required package/container/Python artifacts, a tested base-appliance bootstrap, private site input handling and spare-media acceptance tests. See [Image-to-Ark plan](../30-Developer/BootstrapPlan.md). Do not describe these prerequisites as already cached or the clean-card rebuild as complete.

Use another working computer (which could be the surviving Ark half) and a card reader to prepare replacement boot media. Flashing a selected card is a separate explicit operation; none of these commands selects, repartitions or formats either live drive.

## Quiescent checkpoints and tests

Before declaring a recovery pair, finish or pause content updates, take a Git checkpoint, capture the public content profile, copy its source checkpoint and record verification results. Keep private appliance configuration protected and separate from public content. A full boot-card image would contain passwords, host keys and network identities; it must not be casually published through the library, SMB or anonymous FTP.

Acceptance requires spare media, leaving the originals available for rollback. Test original-card/new-content and original-content/new-card independently. Verify actual articles/images, maps, PDF tools, radio databases, library management, portal behavior and offline operation from a separate client. Reboot each rebuilt appliance and confirm that both desired selections and configuration mirrors persist. Repeat an interrupted rebuild. Only then label the two-way regeneration path supported.

## Latest validation record

See [Recovery validation — 25 October 2026](RecoveryValidation.md) for the isolated recovery drill, kit preflight results and remaining spare-media acceptance work.
