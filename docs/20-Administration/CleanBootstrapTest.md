# Clean-OS software bootstrap acceptance

This test complements [paired-media recovery](PairedRecovery.md) and the [empty-media drill](RecoveryValidation.md). It asks whether the stock coordinator can obtain and configure its declared base software on a clean OS, without borrowing an existing Ark's virtual environment or installed services.

## Separate claims

- **Clean generic ARM64 software phases:** tested on a new Debian 13 generic-cloud ARM64 system disk, with a separate local ext4 content-kit disk.
- **Full START-ARK command on stock Raspberry Pi OS:** requires a physical supported Pi, its OS marker, local-console approval and real network hardware.
- **Content restoration:** has a separate preset approval and acceptance sequence; it is not authorized merely by software setup.

The generic VM test is useful evidence for the first claim. It cannot establish the second by skipping the radio phase.

## Test construction

The disposable guest is separate from the read-only development emulator. The verified Debian cloud image remains an unchanged backing image; a new 64 GiB system overlay and a new 16 GiB content disk hold all writes. SSH and web forwarding bind only to desktop loopback (22223, 18090 and 18091). The guest has its own SSH key and newly generated caretaker credential. Production networking, Home Assistant credentials and community data are not imported.

Cloud-init creates the required `admin` account at UID 1000 and the explicit `/etc/dataark-clean-bootstrap-test` marker. It does not install Ark packages. The public recovery kit supplies source, readable configuration and the documented PMTiles executable; no Python virtual environment is copied.

The blank guest content disk is explicitly identified before formatting, mounted and owned by admin. The kit is copied onto it. That preparation is a test-fixture step; the recovery installer itself does not format drives.

## Phase harness

`deploy/emulator/run_clean_bootstrap_test.py` refuses an unmarked, unrecognized or non-root execution environment. It loads the actual coordinator from the kit, validates the site, checks preflight and runs the real `Installer.phase` methods for packages, source, storage, Python, base services, public distribution, content-policy and finish checks.

The test-site copy explicitly sets `require_raspberry_pi_os` to false for generic Debian. It does not create a fake Pi OS marker or pretend that a virtual Ethernet interface is a Wi-Fi radio. The hardware-specific `network` phase is omitted and recorded as untested. The harness does not exercise the top-level physical installer's local-console/INSTALL interaction; those protections remain in place.

A guest-only generated password is supplied privately to the existing credential installer. The transient password-input file is removed when the harness exits. No production authorization is reused.

## Evidence and checks

Retain the coordinator journal, phase result, package log and source revision. Verify fresh package/venv installation, declared service status, dashboard/API/documentation responses, management authentication and the absence of optional downloads. Reboot the guest and verify service/mount persistence after software phases succeed. Record failures as failures; resuming after a fix does not erase the first-run failure.

Guest evidence locations:

- `/var/lib/dataark/clean-bootstrap-test.json`
- `/var/lib/dataark/bootstrap.json`
- `/var/log/ark-clean-bootstrap.log`
- `/var/lib/dataark/bootstrap-readiness.json` when finish succeeds

Host test instance: `F:\DataArk-Clean-Bootstrap`. Physical acceptance remains governed by [Recovery validation](RecoveryValidation.md); this test never makes the recovery branch eligible to merge on its own.


## Result — 29 October 2026

**Passed after corrections and phase retries, within the generic ARM64 software scope.** This was a clean OS at the start, not a copied Ark installation. The first run was not a pass: the test exposed real bootstrap defects. Reviewed fixes were applied to the disposable guest and the affected phases resumed, with the original failed journals/logs retained.

Corrections now included in source:

- Declare Debian's separate `docker-cli` package, including when preparing kits from older installed-site settings.
- Replace the registry-rejected Kiwix digest with the official Linux ARM64 manifest `sha256:7096f2f2098bbb9ac97f02fe11d51195861a2507667d87a5e8d932fc28106bc2`, resolved and pulled during the test.
- Defer Wi-Fi-role installation until the DataArk AP profile exists. Base authentication/helper installation no longer requires a profile that a fresh system has not created yet.
- Give the reader an empty-library startup path; later restarts discover installed ZIM archives normally.
- Reload Apache after installing the proxy configuration and allow bounded HTTP startup retries.
- Install public distribution independently of radio setup, creating missing stock-Samba share definitions read-only before applying the existing hardener.
- Publish portable index files with explicit `0644` permissions; temporary-file `0600` defaults had denied access on ext4, a problem masked by the original exFAT volume.

Verified dashboard, API, locally hosted API documentation, handbook, library-management page, community page and empty reader: HTTP 200. Caretaker authentication accepted the generated credential; unauthenticated unlock returned 401. Data Ark, Apache, Docker, Samba and Avahi were active. Optional map/archive download timers remained disabled.

Public-file checks passed over HTTP, anonymous FTP and actual SMB. FTP and SMB write attempts were denied; the HTTP private path returned 403 and FTP refused the private directory. The content filesystem and base services returned after a guest reboot. A second reboot after public-distribution setup also passed: the ext4 content mount, API, web pages, empty reader, caretaker authentication, HTTP/FTP checks and actual SMB read all returned successfully. The boot ID changed on both reboots.

**43 relevant regression tests passed** for stock setup, content profiles, queue behavior and public content access. Tests use disk-backed temporary storage so the real 10 GiB reserve is not defeated by a RAM-backed `/tmp`. New checks cover AP/helper ordering, idempotent read-only fresh-share creation and publicly readable generated files.

### Interpretation

This demonstrates the coordinator's real base-software phases installing from package/registry sources on a clean generic ARM64 OS, after correcting the defects found in this run. It is not a second, zero-intervention replay of the final kit from another blank OS. The test harness invoked the real phase methods while explicitly omitting the physical `network` phase and the top-level local-console interaction. Source overlays and reviewed configuration/journal corrections were part of debugging and remain recorded.

It does **not** certify stock Raspberry Pi OS, AP/radio/portal behavior, USB power, physical media swaps, the full optional software/tool inventory, complete content restoration or dependable paired-media recovery. Those remain separate acceptance work. No merge or fully verified Pi-appliance claim is authorized by this result.
