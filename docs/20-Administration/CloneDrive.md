# Clone a content drive

Open **Manage Library → Clone a content drive**. Connect and mount a separate empty drive, reload the drive list, choose a mode and preview. The preview changes no files and starts no downloads.

| Mode | What it copies |
| --- | --- |
| Configuration and software only | Public configuration, restoration recipes, committed source and the Pi setup coordinator. |
| Whole collections that fit | The same kit, plus complete public collections within the available space. |
| All public content | The kit and every eligible public collection; refused if space is insufficient. |

Fit mode prioritizes communication, preparedness and radio study, then smaller collections. Each ZIM archive is a collection; public directory collections are kept together so they are not half-copied. Priorities, collection directories and the default **2 GiB reserve** are readable in `config/clone-policy.json`. A separate conservative allowance covers software and configuration. Filesystem allocation rounding is included.

The preview lists included and skipped collections, capacity, destination mount path and filesystem UUID. Copy its generated command into the caretaker terminal. It requires sudo and the exact reviewed plan ID. Changing configuration, source files, target identity or the selected subset invalidates a fresh plan. The website has no command-execution or cloning-write endpoint.

For a terminal-only preview:

```sh
cd /opt/dataark
sudo venv/bin/python tools/replicate_drive.py --targets
sudo venv/bin/python tools/replicate_drive.py --target /media/admin/NewDrive --mode fit
```

Run the **exact command printed by that preview**, including `--accept-plan` and `--apply`. A running archive, map or recovery worker causes a refusal; stop or finish that work first. The clone operation does not kill workers.

## Destination protection

Use an existing mounted ext4, exFAT or NTFS filesystem. The tool never partitions or formats disks, deletes files, or reuses unrelated files. The boot and live content disks are protected, including their other partitions. Filesystem UUID and backing disk identity matter; USB bridge serial numbers alone are not sufficient.

A destination must be empty apart from filesystem housekeeping directories, or contain this tool’s own matching incomplete clone journal. A completed clone cannot be overwritten by this command. An existing spare-media proof or a manually populated drive is deliberately not treated as an empty destination.

## Interruption and verification

Keep the destination at its original mount path. Preview it again using the same mode. The saved plan supplies a command with `--resume`. Do not edit the hidden `.dataark-clone` journal. If interrupted during the journal’s initial creation before any files were copied, preserve the evidence and inspect the incomplete journal before trying again.

Copies are streamed and SHA-256 verified. Completed files are reused only when both source and destination still match their receipts. A partial file’s entire existing prefix is checked against the source before appending. An unexpected destination file or a mismatch stops copying without overwriting it. The free-space reserve is checked during copying. A disconnected destination stops further writes.

Progress appears on the clone page and in `/var/lib/dataark/cloning/status.json`. The drive retains its plan and per-file receipts. `CLONE-REPORT.json`, `START-HERE.html` and `BROWSE.html` list the verified copied files and skipped collections. Safely unmount after completion.

## What travels with the drive

The kit exports the current public library configuration rather than an obsolete inventory. The full desired collection remains in the portable recipe even when only some payloads fit. Missing content is not advertised as copied; it can be restored later through the separate restoration workflow.

Private household backups, passwords, integration tokens, SSH keys and original hardware assignments are excluded. Each new Ark establishes its own identity. The drive is a content/configuration/software kit, not a bootable OS image. Open `START-ARK.html` for the supported stock-Pi setup procedure. System packages and other software dependencies still require internet; optional content restoration is a separate explicit choice.

See [Stock-Pi setup](../30-Developer/StockPiSetup.md) and [capacity-aware restoration](RecoveryQueue.md) for installation and restoration. Physical spare-system acceptance remains the gate for calling the complete recovery path dependable.

## Copy-worker verification

The October 29, 2026 checks passed 73 cloning, recovery, manifest and documentation regression tests. A separate test used two newly created file-backed ext4 volumes, copied three fixture files (75,000 bytes), interrupted between files, resumed the same plan and checked every SHA-256 again after a read-only remount. It also checked the public source archive and omission of saved Wi-Fi hardware identity. Neither physical content drive was modified.

The repeatable copy-worker proof is available to a developer on the Ark:

```sh
cd /opt/dataark
sudo venv/bin/python tools/test_clone_volumes.py --apply
```

It temporarily creates sparse image files under `/var/tmp`, mounts them, and removes them after the test. It uses fixture content and the saved public recipe to exercise copying; it is separate from installing a fresh Pi or recovering onto physical spare media. Its result is written to `/var/tmp/dataark-clone-proof-result.json`.
