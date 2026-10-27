# Capacity-aware restoration queue

This implementation is experimental on `feature/readme-foundation`. Do not merge or describe paired recovery as dependable until the spare-media acceptance matrix in [RecoveryValidation](RecoveryValidation.md) passes. Automated fixture tests do not replace those tests.

## Presets and explicit approval

Open `/recovery.html` from Manage Library. The page previews four presets against the mounted destination. It is read-only: creating or controlling a queue requires the authenticated caretaker terminal. There is no new passwordless root helper or browser mutation endpoint.

- **None:** no optional content and no downloads.
- **Minimal:** enabled preparedness PDFs up to 16 MiB each and the radio-study package, plus the final indexes. This is an optional preset, not the still-unimplemented built-in seed library.
- **Recommended:** Minimal, larger preparedness references, vehicle files, forms, family resources, resilience references, iFixit and WikiMed where enabled in the saved profile, plus dependencies.
- **Full:** all enabled saved archive, direct-file, map-file and recipe packages. Disabled choices stay disabled. A recipe can restore its complete configured collection; inspect its catalogue before approval.

`config/recovery-presets.json` defines membership. A missing or disabled required dependency and a dependency cycle are errors. The smallest ready independent package runs first; dependencies always precede dependents and indexes run last. A single large package does not jump ahead of small independent references. Partial source failures inside older collection installers retain those installers' existing reporting semantics; a successful recipe process is not a claim of complete curriculum or all publisher sources being available.

The browser suggests Minimal only if it fits; otherwise it suggests None. Nothing is accepted automatically. Bootstrap starts base services but no optional restoration or automatic download timers, including when an old site file says `restore_missing_content: true`. Device setup confirmation is not content-download approval. Enable existing update timers separately after reviewing the restored selection.

## Capacity model

The profile carries installed size, temporary-space requirement and update headroom. Exports measure recipe directories, including auxiliary source ZIPs and databases, add 25% growth allowance, reserve two footprints for recipe staging/extraction, and add 20% update headroom (minimum 16 MiB per package). Direct files use their recorded sizes and one staging footprint. Overlapping recipes/direct files are conservatively counted more than once.

The fit calculation includes cumulative additional installed bytes, the peak staging footprint, update headroom and at least 10 GiB free reserve. Existing size-matching files reduce additional installed bytes; they are still hash-checked when a recorded checksum exists. Unknown package sizes block approval rather than counting as zero. These estimates are not guarantees about future publisher releases. A caretaker may add reviewed bounds to `installed_bytes`, `temporary_bytes`, and `update_headroom_bytes` in the readable content profile, then review a new plan.

Before each package the worker rechecks available space; it pauses if the reserve would be crossed. During child execution it also monitors the reserve. A smaller drive may fit Minimal and Recommended while Full is disabled. None remains possible. No drive is formatted and no existing content is deleted.

## Terminal workflow

From `/opt/dataark`, after exporting a profile from the populated reference Ark:

```sh
sudo venv/bin/python tools/content_profile.py export
venv/bin/python tools/recovery_queue.py plan --preset minimal
```

Review the packages and capacity, then copy that plan's `plan_id`:

```sh
sudo venv/bin/python tools/recovery_queue.py create --preset minimal --accept-plan PLAN_ID
sudo systemctl start dataark-recovery.service
```

`create` records approval but starts no downloads. If the profile, source catalogues, preset policy or coordinator/installer source changed, the old approval is rejected. Incidental changes in free-byte count do not invalidate identity, but insufficient current capacity still blocks creation. The queue does not overwrite an existing queue.

```sh
venv/bin/python tools/recovery_queue.py status
sudo venv/bin/python tools/recovery_queue.py pause
sudo venv/bin/python tools/recovery_queue.py cancel
# Explicitly resume unfinished packages; completed packages stay complete:
sudo systemctl start dataark-recovery.service
# Explicitly recheck all selected packages without deleting content:
sudo venv/bin/python tools/recovery_queue.py restart
```

`dataark-recovery.service` has no timer, boot enablement, automatic restart, or automatic resume. A reboot leaves its journal for inspection and explicit resumption. A changed profile requires preserving/archiving the old state directory and approving a new plan. Do not move that directory while a worker is running. General Pi/SSD/Git profile reconciliation is a separate future task.

## Persistence and progressive access

`/var/lib/dataark/recovery/queue.json` stores the approved plan, attempts, package states, errors and recent transitions. Writes use atomic replacement and fsync. `control.json` communicates pause/cancel, `phase.json` records child phases, and `worker.log` retains caretaker diagnostics. The read-only `/api/recovery/status` and `/api/recovery/presets` endpoints power the progress page.

Direct-file phases include checking, downloading, verifying and publishing. Verified files are renamed atomically into their destination and linked immediately from completed queue entries. Each completed archive refreshes Kiwix and the landing page immediately. Final indexes regenerate the remaining ordinary collection views. Collection recipes retain their own index publication behavior. A failed package does not prevent independent packages from continuing; its dependents remain blocked. No failed direct download becomes a completed link.

Downloads use private mode-0700 staging under `/mnt/storage/.dataark-restoration`. Cancellation terminates the entire child process group and retains partial downloads and verified final files. Full rejected partial files are quarantined for inspection before a retry; they are not published or silently reused. A resumed job checks existing files against recorded size/hash where available. Sources without a recorded hash retain HTTPS/size checks, not a claim of cryptographic verification.

The coordinator holds the archive and map worker locks. Existing collection installers inherit the same real archive-lock descriptor; mismatched descriptors and competing locks are rejected. This avoids deadlocks and concurrent updater writes. A running unrelated updater may prevent queue startup; inspect it and retry rather than deleting lock files.

## Portability boundary

Content profiles, presets and queue logic are largely distro-independent Python. The current bootstrap remains deliberately restricted to Raspberry Pi OS/Debian 13 on AArch64, admin UID 1000, NetworkManager and systemd. apt packages, service installation, permissions, portal/network helpers and Pi-specific configuration require adapters and acceptance tests before another distro is supported. This slice does not broaden the supported baseline, add a built-in seed library, build an offline dependency cache, or prove fresh-Pi recovery.

## Required spare-media acceptance

Use separate media: clean supported OS plus populated SSD, configuration-only SSD, replacement/smaller SSD, upstream loss, corrupt existing/partial files, power loss during download/verification/publication, pause/cancel/resume, and an independently produced second kit. Verify client-visible content and management authentication. Keep the original system and content media intact throughout these tests.
