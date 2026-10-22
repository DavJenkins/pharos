# Reliability acceptance tests

## Automated regression checks

Run from `/opt/dataark`:

```bash
venv/bin/python -m unittest discover -s tests -v
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

## October 22 viewer and distribution audit

Anonymous FTP was tested on loopback and from the desktop LAN: public listing, small-file retrieval and resume succeeded; uploads and entry into staging/private directories were rejected. Documentation and local map indexes returned HTTP 200. These checks do not establish client compatibility for every content format.

Kiwix catalogue and homepage were reachable, but collection-page requests timed out during the live audit while Gutenberg was downloading. Restarting the reader temporarily reset connections; its homepage returned afterward, while archive-page timeouts remained reproducible. A process was observed waiting on SSD reads. This does not establish a disk fault or prove the download caused it; reader performance and article/image access remain unresolved acceptance items. Do not treat a successful catalogue probe as proof of usable article access.

The map audit found 59 topographic PDFs, one flood GIS ZIP, and 114 parcel GIS ZIPs. Collection indexes are linked from the landing page, but GIS ZIPs require external software. No integrated browser GIS viewer is currently provided. The Windows reader package is present; execution on Windows and compatibility with other operating systems are separate acceptance checks.
