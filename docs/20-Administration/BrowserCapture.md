# Browser download capture

[Open capture page](/capture.html). This provides the missing last mile when a public reference downloads in a normal browser but automated retrieval fails. It is limited to explicitly selected public PDFs and verified replacements; it does not collect unrelated downloads or completed personal forms.

## On the Ark Pi / Chromium

Run `sudo python3 /opt/dataark/deploy/install_pi_browser_capture.py` from the Pi terminal. Fully quit and reopen Chromium, then open [the capture page](http://dataark/capture.html). The Debian Chromium launcher loads `/usr/share/chromium/extensions/dataark-capture`. No ZIP extraction, Windows PowerShell, SSH identity or IP-address pairing is needed on the Pi.

The helper reads only explicitly selected approved PDFs under `/home/admin/Downloads`. Registration is `/etc/chromium/native-messaging-hosts/com.dejsoftware.dataark_capture.json`; the on-demand host and local configuration are in `/usr/local/lib/dataark-browser-capture`. A dedicated sudo rule permits only `/usr/local/libexec/dataark-browser-import` with no arguments, invoking the existing validated importer. No browser-controlled shell command or destination path is accepted. This is for the Pi administrator account; public library visitors do not gain installation rights.

Re-run the installer after source upgrades. The source is in the repository and recovery archive. It requires an already configured Ark, mounted content drive, admin account and Debian Chromium launcher; fresh-system acceptance remains separate. To uninstall, remove the extension directory, native registration, local host directory, import wrapper and `/etc/sudoers.d/dataark-browser-capture`, then restart Chromium. Library content remains.

## One-time Windows / Chrome setup

1. Download the capture ZIP from the page, extract it to a permanent folder, and run install.ps1 using PowerShell. Python 3.9+ and Windows OpenSSH must be installed. Keep the extracted extension folder in place. The installer registers the helper for your Windows user account; moving the files later requires updating that registration and loading the extension from its new folder.
2. Open chrome://extensions, enable Developer mode, choose Load unpacked and select that same folder. Extension ID: gilcpcndoddadpkefaeecjemhhcahhig. Chrome requires this local installation step; the Ark cannot silently install an extension.
3. Open http://dataark/capture.html, or use the Ark’s current address followed by `/capture.html`. The page reports whether the extension is connected.

The native helper registration is current-user only at HKCU\Software\Google\Chrome\NativeMessagingHosts\com.dejsoftware.dataark_capture. Its manifest permits only the fixed extension ID. The helper is launched on demand; no background service is installed. Local config.json points to the existing SSH key, known Ark host and permitted download folders. The key is never copied into the extension, sent to the page, or committed. This setup uses the existing authorized root SSH identity rather than a new public upload endpoint. It is an administrator pairing, not a way for every library visitor to install content. Strict SSH host-key verification and batch mode are enforced; authentication failures are reported, not bypassed.

## Normal operation

Choose Download & import for one entry. The extension asks Chrome to download that exact publisher URL into Downloads/DataArk without requesting a save dialog itself. Chrome's own Ask where to save preference, browser warnings and publisher restrictions still apply. After completion the helper automatically reads that selected file and sends it through the fixed local helper on the Pi, or the paired SSH connection on Windows. No folder/file selection is needed when Chrome uses the permitted Downloads folder.

If a publisher requires browsing first, use Open publisher. Capture is armed for that selected original URL for ten minutes. Use the publisher PDF viewer's download/save control. Downloads with a different original URL, including unrelated files or blob URLs, are ignored. Redirected final URLs are recorded separately. Expired capture must be armed again. This cannot promise that every 403 disappears merely because Chrome makes the request.

Status progresses through downloading, validating/importing, and installed or an explicit error. Retry captured files reconnects completed pending downloads after a helper interruption. Reloading reads each collection's sources.json and hides installed items. Original downloaded files stay in that computer’s Downloads folder; the workflow does not delete them.

## Validation and publication

The server derives destination, source and collection from its own catalogue, not a browser path. Approved PDF IDs and identity checks are fixed in tools/import_browser_reference.py. Limits: 30 MiB, 2,000 pages, PDF parser timeout and unencrypted files. Required document identity/year text must appear in the first three pages; mismatches and draft tax returns are rejected. Conservative rejection is intentional: an administrator can review an unusual scanned document separately. Signature/hash validation proves structural identity and records the imported bytes; it is not a cryptographic publisher signature.

The existing family/forms/resilience installer performs its normal validation and registration. Installed files can be replaced only after an explicit selection carrying their current SHA-256. A stale baseline is rejected; same-byte comparisons are idempotent. Previous verified bytes and metadata are retained under /var/lib/dataark/browser-capture/history, outside public content shares. The helper updates sources.json with browser-acquisition provenance, collection index, manifest, public content configuration and portable catalogue, then redeploys the web interface. A mounted content drive and existing filesystem/SSH administrator authorization are required. A capture lock serializes capture imports; existing installer worker-lock checks still apply. Publication errors are reported; inspect the inventory before retrying because a validated file may already have been recorded before a later deployment failure.

The machine-readable gap register removes an imported entry from unavailable_entries and records it in resolved_entries. The narrative ContentGaps guide is now regenerated from the gap JSON after each import, so successful captures appear under resolved entries. Subject-coverage assessments still require editorial review. Automatic imports do not create commits or push GitHub. Review provenance and exported configuration before the next intentional source/recovery checkpoint.

## Sources and rebuild

- Extension/native host source: /opt/dataark/tools/browser-capture/.
- Fixed SSH importer: /opt/dataark/tools/import_browser_reference.py.
- Package builder: tools/build_browser_capture.py. It uses the reviewed gap register and source catalogues to generate targets.json, the public target list and a reproducible ZIP. Run it after changing approved source URLs or closing gaps; update the extracted extension/helper and reload Chrome when targets change.
- Static page: app/static/capture.html and assets/js/browser-capture.js.
- Tests: tests/test_browser_capture.py and tests/test_browser_capture.mjs. Native boundary, wrong identity/year, encrypted/non-PDF, unrelated download and wrong page-origin behavior are covered. Browser tests use mocked Chrome APIs; actual Chrome extension/native-host delivery must be checked after loading it.
- [GitHub source](https://github.com/DavJenkins/pharos), branch feature/readme-foundation.

No SSH key or local config.json belongs in Git or the public ZIP. Uninstall the extension in Chrome, remove its current-user native-host registry key, then remove the extracted folder. Existing content and original downloaded copies remain.

## Version 1.1 update lifecycle

Installed captures remain in a collapsed section, outside the pending list. Check installed captures for updates explicitly asks the paired desktop helper to run bounded publisher checks on the Ark. No periodic scheduler is added. Validated PDF bytes are compared to the installed SHA-256: identical means current; different means changed and needing review, not proof of a newer edition. An unparseable file or failed HTTP request is unknown/blocked; the installed copy stays usable.

Verified installed browser captures use the source-specific review intervals in `deploy/reference/browser-capture-policy.json`: annually for archived CDC materials and pinned tax forms, every 90 days for code amendments. The capture page computes due dates on every visit; no explicit publisher check is needed to make an overdue review visible. Manage Library shows the same schedule and links due items to Capture downloads. Weekly automated source retries continue. A known HTTP 403 for a configured, installed browser capture is informational, while overdue reviews, validated changes, and unexpected errors need attention. A successful automated comparison resumes normal automated status; a browser comparison resets the review date. Dates use the viewing device’s timezone.

A valid changed copy requires the current baseline hash and preserves the previous verified PDF and metadata privately before replacement. Year-specific forms retain their year: a later tax year requires a separate entry. Changed bytes alone do not establish a newer edition.

Home Assistant receives the read-only `source_checks.browser_review` object through `/api/health`: required and overdue counts, individual titles, last verification, next review dates, intervals, and the capture-page link. Stable health fingerprints change on reviews becoming due, completion, detected changes, and automated-check recovery, rather than on every poll. Overdue reviews create a health warning; a known blocked automated check alone does not. The HA package records transitions, exposes review counts, and includes source-check context in `dataark_health_changed`.

The dashboard uses the same health report. While idle, the status box condenses after 30 seconds to a gear: green for healthy, amber for warnings, red for failures, and gray for unknown or stale status. Warnings and failures include an attention-count badge. A new issue expands the box for 30 seconds; tapping the gear shows the issues and action links. Active downloads, verification and other ongoing work keep progress visible. Publisher-check issues and overdue reviews link to Capture downloads; the System popup’s Library tab also links to scheduled browser reviews. Configured reviews that are not due remain informational.

Update observations live in /var/lib/dataark/browser-capture/update-checks.json, with a public non-sensitive view at /library-files/browser-capture-status.json. They are runtime observations rather than content selection. Previous-copy history is on the system disk; it is not included in the public library or automatically replicated as payload. An administrator can recover an earlier PDF and its saved sources record after checking its SHA-256. No automatic history deletion policy is installed.

When upgrading this unpacked extension, replace package files while retaining local config.json and the native-host launcher/registration, then click Reload on its card at chrome://extensions and refresh the capture page. Permissions and extension ID are unchanged.


## Source failures and replacement review

The capture page separates missing files, broken links, browser checks, and installed captures that need no action. A 403 is an access refusal, not proof of a missing publication. Changed bytes require review and do not prove a new edition. New editions discovered by the scheduled publication rules appear separately in Manage Library.

`deploy/reference/capture-sources.json` records the publication page where verified, the current download URL, assessment date, failure classification, and any reviewed replacement candidate. `discovery_rule: null` explicitly means there is no automated edition-discovery rule for that source yet. This file travels with recovery configuration. Download identities and permitted URLs remain pinned to the catalogue; metadata does not broaden importer permissions.

The October 27 assessment found nine installed captures with blocked automated checks, four missing publications requiring browser checks, and three missing publications with confirmed 404 URLs. Broken links have no capture action. The Forest Service recreation checklist is a working related candidate, not a verified identical replacement for the older brochure. Its review link does not arm capture.
