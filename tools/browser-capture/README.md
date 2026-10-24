# Data Ark browser capture

This folder is a Chrome extension and its Windows native-messaging helper. It only captures explicitly selected, known public references. It does not collect unrelated browser downloads. The extension receives no SSH private key or caretaker password.

1. Keep this extracted folder in a permanent location.
2. Run `install.ps1` with PowerShell. It registers only this extension's fixed ID in the current user's Chrome native-messaging registry. It does not install the extension or alter Chrome download preferences.
3. Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select this folder.
4. Open `http://dataark/capture.html` or the Ark's IP-address equivalent. Choose **Download & import**.

For a publisher that requires browsing first, choose **Open publisher**, then use that PDF viewer's download button within ten minutes. The original download URL must match the selected reference. Downloads with unrelated URLs are ignored. Chrome's save-location prompt, if enabled, still applies; the helper accepts files only inside configured download folders.

`config.json` is local configuration, not part of the public package. It selects the Ark host, existing SSH identity, OpenSSH executable and allowed Downloads folders. The default uses this Windows user's existing `.ssh/id_rsa`, the Ark at `192.168.40.123`, and the standard Downloads folder. SSH host-key verification must already succeed. Password and host-key prompts are not bypassed. The helper uses the existing root SSH authorization solely for a fixed import command; pairing requires an authorized Ark administrator. Review this configuration if installing on another computer. Never put a private key in this folder.

The import accepts approved PDFs only, validates document identity/year, parses with Poppler, hashes the file and uses the existing collection installer. A selected replacement must match the installed baseline hash; the previous verified copy is retained privately on the Ark before replacement. The original desktop download stays in Downloads. Metadata, index, manifest and portable configuration are refreshed; no Git commit/push happens automatically. The machine-readable gap record is updated; the narrative gap report is regenerated from the reviewed JSON assessment after each import.

Version 1.1 adds **Check installed captures for updates**. Checks are explicit/manual, not scheduled. A successful check compares actual validated bytes; changed bytes are marked for review, not automatically called a newer edition. A blocked/unknown check keeps the local copy and offers browser comparison. Capturing the same bytes clears that request. Pinned tax years remain pinned; a later year needs its own catalogue entry. Up-to-date installations stay out of the pending list and remain in a collapsed installed section. Update checks and automatic captures require Chrome with the extension loaded.

If the helper is interrupted, use **Retry captured files** on the capture page. A successful installation is visible in the collection and no longer appears in the capture list after reload. A failed PDF/identity check does not mean the source is private. No content is installed merely because a download returned HTTP 200.

To uninstall, remove the extension from Chrome and delete the current-user registry key `Software\Google\Chrome\NativeMessagingHosts\com.dejsoftware.dataark_capture`. Delete this folder only afterward. The helper is launched on demand; there is no continuously running background service.

Blocked checks leave recent successful captures resolved for 30 days by default (configurable on the Ark). Prior verified replacement copies are retained privately on the system disk; they are not public library downloads. No scheduled checks or automatic history pruning are installed.
