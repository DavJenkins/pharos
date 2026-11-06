# Reliability acceptance tests

## Automated regression checks

### Measured Python coverage

Use a separate Linux test environment so test tools do not change the running appliance's dependencies:

```bash
python3 -m venv .venv-test
.venv-test/bin/python -m pip install -r requirements.txt -r requirements-test.txt
mkdir -p "$HOME/dataark-test-scratch"
export TMPDIR="$HOME/dataark-test-scratch"
umask 077
.venv-test/bin/python -m coverage run -m pytest tests
.venv-test/bin/python -m coverage report
.venv-test/bin/python -m coverage html
.venv-test/bin/python -m coverage json
```

The report covers Python in `app`, `tools` and `deploy`, including files that were never executed. Read the test result before interpreting a percentage: collection errors mean the suite did not run. Line execution and branch coverage do not prove safe behavior under interrupted downloads, missing drives or physical network changes. JavaScript logic tests and browser/device acceptance are separate checks; this Python percentage does not include them. The HTML report is written to `output/coverage/html/index.html`.

Use Linux scratch storage with enough free space for the update reserve checks; the Pi's small memory-backed `/tmp` is unsuitable for that suite. Run the two privileged restoration subprocess cases separately. Their fixtures use temporary content and a fake downloader:

```bash
sudo env TMPDIR="$TMPDIR" .venv-test/bin/python -m pytest tests/test_recovery_queue.py::RealWorkerTests -v
```

If Node.js is installed, run the browser-logic checks as well:

```bash
node tests/bugout.test.js
node tests/connectivity.test.js
node tests/portal.test.js
node tests/ark-connectivity.test.js
```

The tests use temporary storage and simulated services. They do not trigger real household backups, manipulate the live firewall, or contact Home Assistant.

| Case | Automated coverage |
| --- | --- |
| SMB exits zero but reports access denied | test_bugout: rejects the incomplete result and removes the partial file |
| Recover binary content with a Unicode filename | test_bugout: actual producer subprocess, tar reading, byte-hash comparison |
| SSD disappears or fills during a copy | test_bugout: stops the child, removes partial output, preserves existing backup |
| Corrupt normal refresh | test_bugout: preserves last good archive and its cache link |
| Source reachable after failed backup | test_bugout: failure remains in status independently of reachability |
| HA acknowledgement lost | test_bugout: retried delivery retains event and operation IDs |
| Cancellation, background continuation, priority, budget | existing test_bugout cases |
| Offline portal, untrusted caller, per-device controls | test_portal and test_pass_through |
| Content activation/publishing failure | test_content_activation rollback and recovery-journal cases |
| Browser connectivity and disabled actions | JavaScript suites above |

A passing test for retained failure data does not prove the warning is prominent enough in the UI. Retry backoff now has automated progression/cap/reset coverage, and browser tests check persistent warnings and recovery. A retention policy remains product work.

## Controlled live acceptance checks

Record device/OS, date, expected result, actual result, and relevant status output. Use disposable source files and no active production transfers for disruptive checks.

1. **Portal without upstream:** on Android, Apple and Windows clients, forget/rejoin DataArk with alternate internet disabled. Verify the sign-in prompt where supported, the landing page, local library access and disabled external links. Confirm `http://192.168.4.1/` always works manually. Do not expect HTTPS interception.
2. **Two clients:** enable pass-through on client A; verify A reaches an external site while B remains blocked. Both must retain local content access. Disable A and repeat. Check lease expiry and reconnect behavior.
3. **Reboot recovery:** after all transfers finish, reboot the Pi. Verify portal/API/Kiwix readiness, public local access and pass-through off by default. Verify maintenance resumes without calling interrupted work successful.
4. **Household recovery:** snapshot a small disposable directory containing text, binary and nested files. Extract into a separate test directory; compare names and hashes. Repeat with one unreadable file and verify failure is visible and the prior successful snapshot survives. Restore test permissions afterward.
5. **HA:** with physical-device automations disabled, trigger once in each direction, retry the same operation ID, cancel with and without background continuation, and interrupt HA connectivity. Verify duplicate events do not duplicate the household automation. Normal sync must emit no bugout trigger.
6. **Encryption:** use a disposable recipient key and sample source. Decrypt on another machine and compare hashes. Test missing/wrong public keys. Never use a test that depends on deleting the only private key.
7. **Portable SSD:** shut the Pi down cleanly before unplugging the SSD. Mount on Windows, open START-HERE.html, inspect the catalog, read documents and open a ZIM in a compatible reader. Restore the SSD and reboot the Pi.
8. **Missing SSD / interrupted updates:** exercise on a spare appliance or disposable storage. Ensure no content is written into the unmounted mount-point directory, old content survives update failure, and status identifies recovery work. Do not pull a live production SSD to simulate failure.

Retention limits, UPS behavior and application-specific database consistency need agreed policies and implementations before acceptance criteria can be finalized.

## Reader and distribution acceptance

Check representative articles and images through each installed Kiwix collection, not just the reader homepage. Check the local map viewer and a representative installed region. GIS ZIPs are downloadable datasets and require a compatible external application; a successful download does not establish browser viewing support.

For anonymous FTP, verify public listing, a small-file retrieval and resume, rejection of uploads, and denial of private/staging paths. Repeat from an actual client on the intended network. The Windows reader package needs a Windows execution check independent of its presence in the catalogue.

Keep completed results tied to the source revision and tested media. See [Release audit](ReleaseAudit.md), [Paired recovery](PairedRecovery.md) and [Desktop ARM64 test Ark](Emulator.md) for the corresponding procedures and records. A historical fault log is not the current acceptance checklist.


## KZ1O retained-build online upgrade

Use the prepared KZ1O microSD as an existing recipient installation, retaining its original build. Do not reflash it, copy current application files onto it, or re-enroll its software baseline before this test. Its populated system-card library and special-edition settings are part of the preservation test.

1. Before booting or changing the card, make and verify a restorable card backup. Record the physical media identity and backup digest privately. Retain the printed setup identity; do not regenerate its setup code solely for this test.
2. Boot the old card and record its build identity, installed update receipt, enrolled trust key fingerprint and managed-file hashes. Inspect existing local modifications without accepting them into a replacement baseline.
3. Record a preservation inventory: installed content hashes, library configuration, KZ1O edition notice, installed-only preference, community data, banner, credentials, host/clone identity and network settings. Keep private values out of public test reports.
4. Verify the starting installation over Ethernet and its hotspot. Record actual problems as starting conditions rather than concealing them.
5. Publish a signed preview software release applicable to the recorded base revision. Review the complete required file set and updater capabilities first. The version-1 updater excludes privileged helpers, service definitions, dependency changes and schema migrations. Do not ship new application endpoints that depend on an omitted helper. An unsupported required change blocks that release; it is not a successful full upgrade.
6. Complete pending first-owner setup through the existing code flow. If the retained build predates on-Ark acquisition, first use its existing signed-package upload/stage/install flow to install the bridge. Then use Help, Check for updates, Download and verify on the Ark, and Install verified update with caretaker authorization. Record the separate verifier transition and both acquisition paths. Use the recipient-facing online workflow; no manual SSH file replacement counts as this test.
7. Verify signature/base/local-edit refusals separately on a disposable copy. Exercise interrupted download and failed-health rollback on that copy; never deliberately corrupt the only recipient card.
8. Confirm the resulting release identity, installation history, API, dashboard, handbook and content readers. Compare the preservation inventory, including the amateur callsign database. Confirm credentials and special-edition identity remain usable and no new first-run activation is requested unexpectedly.
9. Cold-boot the upgraded card. Verify hotspot visibility, captive portal, Ethernet access, installed content and system health. Then test disconnected operation, reconnect and check for updates again.
10. Capture Home Assistant lifecycle results where the recipient installation is configured for it. Record the outcome and any limitations, retain the verified backup, and only then approve this card for mailing.

A successful application-only transaction establishes only that declared scope. Full release acceptance requires every required component of that release to arrive through the supported upgrade workflow, with a tested rollback path. Preserve the old card until a suitable package and any necessary updater transition are ready.
