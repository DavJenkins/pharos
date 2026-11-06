# Release validation

## Retained-build bridge acceptance — November 6, 2026

The retained KZ1O system-card installation was backed up and verified before booting. Its original receipt identified source `2245a6c308cbac2f0e03ec49b13b19cbfa852e96`, sequence 0. The separately signed verifier transition retained the existing receipt rather than re-enrolling changed files. First-owner setup was completed through the ordinary pairing-code endpoint for the test.

The original build supported signed-package upload but predated on-Ark package downloads. Its first package therefore used the existing authenticated upload/stage/install API. Preview 1 failed during dashboard regeneration and automatically restored the old software and receipt. The cause was an unprivileged renderer trying to rewrite identical root-published artwork. Immutable-artwork reuse fixed that failure without changing permissions. The corrected preview passed a real recipient-configuration rendering check before another live installation.

`software-2026.11.06-preview.2`, source `fa1cfaaa0acf7aef31cb57cee35fc2fd785d53c7`, completed on the physical Pi and advanced its receipt to sequence 1. Health reported `ok`, no problems and no managed-file drift. The KZ1O notice and installed-only preference remained. The before/after inventory retained all 1,777 library files with unchanged size and modification time; the separate live usage counter changed normally. These are metadata-preservation checks, not a second hash of every content file.

The API, engineering handbook and Kiwix homepage responded successfully. The installed 469 MB FCC database returned the expected callsign search and grid-proximity results with distance and bearing. The update/artwork suite passed 45 isolated tests. The exact package also passed disposable-copy installation and failed-health rollback.

This record distinguishes the verifier transition, original upload path, live automatic rollback and successful bridge installation. Browser automation was unavailable; the authenticated HTTP endpoints used by the page were exercised directly. Subsequent on-Ark acquisition and reboot acceptance are separate checks. No merge was performed.

## On-Ark follow-up and offline acceptance — November 6, 2026

After the bridge, the Pi discovered `software-2026.11.06-preview.3`, downloaded its 1,400,704-byte archive directly from GitHub, verified it and installed all 641 inventoried files through the caretaker-authenticated online API. Its receipt advanced to source `50b454f3a8dae237845a28562d7aa57df5e27fb2`, sequence 2, with no managed-file drift. A physical reboot retained the release, mounted system-card library and active hotspot, with no failed systemd units.

A Windows client joined the real DataArk hotspot. Local dashboard and API access passed; Windows and Android HTTP detection probes both redirected to the Ark landing page. The protected network API refused disabling the hotspot carrying that client's session. Ethernet was then temporarily disabled through the API, with upstream Wi-Fi disconnected. The offline dashboard, an installed Unix Stack Exchange archive page, a local PDF and the callsign search all worked. Software discovery correctly reported unavailable while offline. Ethernet was restored through the same API without changing saved profiles.

Public/private library configuration, reference settings and saved NetworkManager profiles matched the starting inventory. The caretaker record changed only through the explicitly authorized test enrollment. Community messages and metadata matched logical digests recovered from the verified pre-upgrade image; SQLite integrity passed. Its WAL/shared-memory files changed normally during service use. Update lifecycle records included verification/pending, successful installation and the earlier rollback in the local HA-compatible durable feed. The recipient has no configured outbound Home Assistant ownership credentials.

The additional copy-first interface change is covered by six browser-logic tests: default copying from a mounted library, disabling copying when missing, retaining an explicit opt-out, never copying over an adopted populated drive, invalidating a plan after source disconnection, and refusing to continue when source status is unknown. The underlying verified-copy backend was unchanged.

## Recipient presentation preservation

Final first-owner-page review found that an approved masthead customization existed on the retained card but not in its authoring template. Its approved header was recovered from the verified pre-upgrade image and incorporated into source; current setup wording and password behavior were retained. Plaintext masthead placeholders in the shared pages were replaced with the existing approved product artwork. No lettering pixels or crop geometry were changed.

The setup form and both external-storage pages passed isolated real-browser checks at 390px and 1280px: no horizontal overflow or script errors. The password-eye control hid and restored its repeat field. All mutation requests were blocked in this visual test. The desktop/mobile setup preview used a simulated pending-setup response, not another actual enrollment.

## Preview deployment audit — October 30, 2026

The refreshed preview is built from source revision `8dd8b4abb6b0cabe3fec2878d5a5d2cc7876e26a` on `feature/readme-foundation`. The normal web deployment script completed inside a private mount namespace, with its output redirected to a staging web root and the library mounted read-only. The live site was not replaced by this test.

| Check | Result |
| --- | --- |
| Local landing-page links and required assets | 1,497 checked; no failures |
| Kiwix archive entry pages | All 8 served actual content |
| Reader resources | Representative local CSS, JavaScript and images served; Gutenberg’s required CSS/JavaScript and normal favicon served |
| Caretaker boundaries | 11 anonymous mutation requests rejected with HTTP 401 |
| Focused Python regressions | 106 passed |
| JavaScript regressions | Backup interactions, public polling and compact health states passed |
| Deployment persistence | Capture status styling, webpage reviews, library contrast, compact notices, maker/sign links and grouped backup actions retained |

Gutenberg’s supplied archive references two absent favicon PNGs. Its normal favicon and required reader resources work. The original archive is unchanged.

The final committed revision was used for the deployment replay, 106 Python tests and corrected quick-start kit. The kit includes `RELEASE-VALIDATION.json`, source identity and checksums. Publisher links are external references and are not counted among the local HTTP passes.

This audit covers deployment, serving and authentication boundaries. Earlier clean-system bootstrap and paired-recovery evidence remain separate; physical spare-media acceptance is still required before calling recovery dependable. No merge was performed.

[Release and bootstrap guide](../00-Introduction/BootstrapDownload.md) · [Engineering](../30-Developer/Engineering.md)
