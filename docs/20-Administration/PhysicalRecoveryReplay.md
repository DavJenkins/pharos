# Physical recovery replay — November 2, 2026

The Raspberry Pi 4 test used a separate 128 GB microSD, without the original content SSD. The frozen kit at `f0479108b4d785e1e651ca7dd33d0b2825872088` completed its ten installation phases. Its clean-install acceptance failed: the OS-update monitor lacked a writable collection-event directory. This result remains failed even though a repaired installation subsequently worked.

## Verified on the repaired installation

- A 4 GiB system-card library contained a checksum-verified 100-article Wikipedia sample and two Ark guide PDFs.
- Services and the sample article/image passed pre- and post-reboot checks.
- Recipient enrollment replaced device identity, removed provisioning SSH access and accepted separately chosen caretaker and Linux-admin passwords through the hotspot.
- The user confirmed sample text and image access on a phone over DataArk Wi-Fi.
- A serial- and capacity-checked spare USB drive was explicitly authorized for erasure and prepared as exFAT.
- The library copy was SHA-256 verified, activated on the external drive and retained the original system-card image.
- After restoring a powered USB hub, the external drive mounted automatically at boot. API health was OK, its library capacity was about 476.9 GiB, and the user confirmed article/image access again.

The power or cabling cause of earlier USB/network failures was not isolated. Keep the known-working powered hub for the replay; the Y-cable arrangement is a separate investigation.

## Findings incorporated into the next candidate

The source fixes create the event directory before starting the monitor; request an explicit `lsblk` partition tree; exclude regenerated usage exports from collection identity; pause the usage writer during handover; retain verification in a private receipt independently of queue status; and use explicit exFAT mount ownership/file masks without Unix per-file ownership changes. The shared masthead stylesheet is included in deployment. The UI highlights the installed sample, links the external-drive migration page, and limits the affiliations/coffee novelty to a collapsed Help/About note.

The manual preparation script also exposed an overlong exFAT label and Windows executable line endings; corrected scripts use a short label and LF interpreter lines. These were test-support script failures, not reasons to erase content again.

## Evidence and next acceptance

The source stays on `feature/readme-foundation`. Desktop acceptance evidence includes `physical-replay-20261102-evidence.tar.gz`; the test host retained installation, pre/post-reboot and repair records under `/var/lib/dataark/acceptance/physical-clean-demo-20261101`, and spare-drive records under `/var/lib/dataark/acceptance/spare-drive-20261102`. Later transfer and phone observations are recorded above from the API and the user's confirmations; they are not a claim that every on-card log was exported.

Next: write a fresh stock Pi OS card with a checksum-pinned corrected kit; repeat installation with the original SSD and spare disconnected; require no manual source or permission repair. Verify healthy services, article/image access, reboot, and the installed UI. Repeat recipient and external-drive acceptance as needed against that frozen revision. Do not merge or describe recovery as dependable until the clean spare-media acceptance passes.


## Corrected frozen-kit replay — passed

A fresh physical Raspberry Pi OS card booted the pinned kit from source revision `2245a6c308cbac2f0e03ec49b13b19cbfa852e96`, with no USB content disks attached. All ten installer phases completed. The frozen kit remained byte-for-byte unchanged, and no manual source, permission or service repairs were applied.

Pre- and post-reboot acceptance passed with different boot IDs, healthy API status and zero failed services. The system-card library remained mounted at its 4 GiB allocation; the Wikipedia archive and two guide PDFs matched their expected hashes. An article and archive image, local pages, caretaker authorization, desktop launch/artwork/splash and OS-update monitoring passed. The installed sample is the first card and is prominently linked; the migration link and shared masthead stylesheet were present. The personal-note script has its Help/About page gate.

Evidence is retained as `physical-clean-2245a6c-evidence.tar.gz` and `acceptance-summary.json` in the desktop’s `physical-replay-20261102-clean` acceptance folder. The earlier clean-run failure and repaired-run success remain separate records. This result establishes the physical stock-OS card-only bootstrap and reboot path; it does not retroactively turn the repaired external-drive walkthrough into an untouched test of this exact revision. No merge was performed.
