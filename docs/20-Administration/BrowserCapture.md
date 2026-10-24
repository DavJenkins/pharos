# Browser download capture

[Open capture page](/capture.html). This provides the missing last mile when a public reference downloads in a normal browser but automated retrieval fails. It is limited to explicitly selected missing PDFs; it does not collect unrelated downloads or completed personal forms.

## One-time Windows / Chrome setup

1. Download the capture ZIP from the page, extract it to a permanent folder, and run install.ps1 using PowerShell. Python 3.9+ and Windows OpenSSH must be installed. On Dave's computer the prepared folder is C:\DEJSoftware\tools\DataArkBrowserCapture.
2. Open chrome://extensions, enable Developer mode, choose Load unpacked and select that same folder. Extension ID: gilcpcndoddadpkefaeecjemhhcahhig. Chrome requires this local installation step; the Ark cannot silently install an extension.
3. Open http://dataark/capture.html (or 192.168.40.123 / 192.168.4.1). The page reports whether the extension is connected.

The native helper registration is current-user only at HKCU\Software\Google\Chrome\NativeMessagingHosts\com.dejsoftware.dataark_capture. Its manifest permits only the fixed extension ID. The helper is launched on demand; no background service is installed. Local config.json points to the existing SSH key, known Ark host and permitted download folders. The key is never copied into the extension, sent to the page, or committed. This setup uses the existing authorized root SSH identity rather than a new public upload endpoint. It is an administrator pairing, not a way for every library visitor to install content. Strict SSH host-key verification and batch mode are enforced; authentication failures are reported, not bypassed.

## Normal operation

Choose Download & import for one entry. The extension asks Chrome to download that exact publisher URL into Downloads/DataArk without requesting a save dialog itself. Chrome's own Ask where to save preference, browser warnings and publisher restrictions still apply. After completion the helper automatically reads that selected file and sends it through the existing SSH connection to the fixed import command. No folder/file selection is needed when Chrome uses the permitted Downloads folder.

If a publisher requires browsing first, use Open publisher. Capture is armed for that selected original URL for ten minutes. Use the publisher PDF viewer's download/save control. Downloads with a different original URL, including unrelated files or blob URLs, are ignored. Redirected final URLs are recorded separately. Expired capture must be armed again. This cannot promise that every 403 disappears merely because Chrome makes the request.

Status progresses through downloading, validating/importing, and installed or an explicit error. Retry captured files reconnects completed pending downloads after a helper interruption. Reloading reads each collection's sources.json and hides installed items. Original downloaded files stay on the desktop; the workflow does not delete them.

## Validation and publication

The server derives destination, source and collection from its own catalogue, not a browser path. Approved PDF IDs and identity checks are fixed in tools/import_browser_reference.py. Limits: 30 MiB, 2,000 pages, PDF parser timeout and unencrypted files. Required document identity/year text must appear in the first three pages; mismatches and draft tax returns are rejected. Conservative rejection is intentional: an administrator can review an unusual scanned document separately. Signature/hash validation proves structural identity and records the imported bytes; it is not a cryptographic publisher signature.

The existing family/forms/resilience installer performs its normal validation and registration. Already installed entries are never overwritten. The helper updates sources.json with browser-acquisition provenance, collection index, manifest, public content configuration and portable catalogue, then redeploys the web interface. A mounted content drive and existing filesystem/SSH administrator authorization are required. A capture lock serializes capture imports; existing installer worker-lock checks still apply. Publication errors are reported; inspect the inventory before retrying because a validated file may already have been recorded before a later deployment failure.

The machine-readable gap register removes an imported entry from unavailable_entries and records it in resolved_entries. The narrative ContentGaps guide is a dated audit and requires later editorial review; the capture page's live inventory is the current operational view. Automatic imports do not create commits or push GitHub. Review provenance and exported configuration before the next intentional source/recovery checkpoint.

## Sources and rebuild

- Extension/native host source: /opt/dataark/tools/browser-capture/.
- Fixed SSH importer: /opt/dataark/tools/import_browser_reference.py.
- Package builder: tools/build_browser_capture.py. It uses the reviewed gap register and source catalogues to generate targets.json, the public target list and a reproducible ZIP. Run it after changing approved source URLs or closing gaps; update the extracted extension/helper and reload Chrome when targets change.
- Static page: app/static/capture.html and assets/js/browser-capture.js.
- Tests: tests/test_browser_capture.py and tests/test_browser_capture.mjs. Native boundary, wrong identity/year, encrypted/non-PDF, unrelated download and wrong page-origin behavior are covered. Browser tests use mocked Chrome APIs; actual Chrome extension/native-host delivery must be checked after loading it.
- [GitHub source](https://github.com/DavJenkins/pharos), branch feature/readme-foundation.

No SSH key or local config.json belongs in Git or the public ZIP. Uninstall the extension in Chrome, remove its current-user native-host registry key, then remove the extracted folder. Existing content and original downloaded copies remain.
