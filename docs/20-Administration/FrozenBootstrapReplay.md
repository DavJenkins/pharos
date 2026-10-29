# Uninterrupted clean-OS bootstrap replay

**29 October 2026 — PASS for the generic ARM64 software phases.**

A second fresh Debian 13 ARM64 VM installed the corrected public kit in one invocation, without source patches, manual package workarounds, phase retries or journal corrections. All eight software phases completed, all 43 relevant regressions passed, and the installed services and content mount returned after reboot.

This is the uninterrupted replay that remained outstanding after the earlier fix-and-retry run. It is not physical Pi, hotspot or paired-media certification.

## Frozen inputs and clean start

- Tested source: `5b15cc6656d623e738ca9e143ecfb4e07c6e2024` on `feature/readme-foundation`.
- Source archive SHA-256: `e87a3df601d60c99eac8cf8ea474d25de25b5f0a6c1c30ec269f5588c38b8431`.
- Coordinator SHA-256: `7a67a9c7cf79ce355ff46122ce94c3480cb7089d9e751829451666a15e1e02ee`.
- The Debian backing image was rechecked against its retained official SHA-512 manifest. New system/content overlays and a new SSH identity were created; no existing Ark virtual environment, installed service tree or writable system disk was copied.
- The prepared VM had no `/opt/dataark` checkout or bootstrap journal. A separate blank 16 GiB content disk was explicitly identified, formatted as ext4 and supplied with the public configuration/recovery kit. Disk preparation was a fixture step, not installer behavior.

The frozen source archive, coordinator, PMTiles executable, site settings and kit manifest retained identical checksums before and after installation. All **221** checked Python/shell/requirements files matched the source archive; the installed document-input checksums matched it too.

## One installation sequence

The log contains exactly one occurrence of each phase, in this order:

1. System packages
2. Source
3. Storage
4. Python environment and dependencies
5. Base services
6. Public content distribution
7. Content-selection policy (no optional downloads)
8. Finish/readiness

The installer run took 716 seconds, excluding VM preparation and subsequent verification. A fresh guest-only caretaker password was supplied privately to the existing installer prompt. The original kit files were not changed to enable the generic VM test: the committed phase harness used its explicitly documented `require_raspberry_pi_os=false` test-site copy and omitted the physical network phase.

The fixture initially stopped at marker/identity safety checks, before formatting or invoking the coordinator. Those preparation issues were corrected and their logs retained. They were not installer failures or installation retries. The subsequent one installer invocation had no interventions.

## Acceptance checks

- Dashboard, API root, bundled API documentation, handbook, library-management page, community page and empty Kiwix reader: HTTP 200.
- Correct caretaker authorization: HTTP 200; unauthenticated unlock: HTTP 401.
- Data Ark, Apache, Docker, Samba and Avahi: active.
- Public HTTP files and anonymous FTP/SMB reads: passed.
- FTP write attempt: 550; SMB write attempt: access denied and no file created.
- HTTP private-directory access: 403; FTP private-directory access: denied.
- Optional archive/map download timers: disabled.
- **43** stock-setup, content-profile, restoration-queue and public-access regression tests: passed using disk-backed temporary storage.
- Reboot: boot ID changed; the ext4 content volume, services, authentication, empty reader, public HTTP/FTP access and SMB read all returned. The installer was not rerun.

## Evidence and reproduction

[Machine-readable result in the source repository (online)](https://github.com/DavJenkins/pharos/blob/feature/readme-foundation/docs/20-Administration/FrozenBootstrapReplay.json) records frozen inputs and checked outcomes. The fixture used is retained as `deploy/emulator/run_frozen_replay.py`; the committed software-phase harness came from inside the frozen source archive.

Host instance: `F:\DataArk-Bootstrap-Replay-20261029`. Guest evidence is under `/var/lib/dataark/` (`uninterrupted-replay.json`, `replay-source-verification.json`, `replay-final-attestation.json` and service verification JSON), `/var/log/ark-uninterrupted-bootstrap.log`, and `/var/tmp/uninterrupted-regressions.log`. A non-secret evidence copy is retained in the desktop workspace. Guest credentials and SSH private keys are not part of the public report or kit.

## Remaining acceptance boundary

The test ran the real coordinator's software-phase methods on generic ARM64 QEMU. It omitted the physical `network` phase and top-level local-console/INSTALL interaction. It does not establish Pi radio/portal behavior, stock Raspberry Pi OS acceptance, USB/power reliability, optional development-tool completeness, content restoration or physical paired-media recovery.

The next acceptance step needs a supported physical Pi and spare media. Keep the recovery work on the feature branch; do not merge or describe paired regeneration as dependable until the spare-media matrix passes. A supported downloadable bootstrap remains gated on that work.
