# Release validation

## Retained-build bridge acceptance — November 6, 2026

The retained KZ1O system-card installation was backed up and verified before booting. Its original receipt identified source `2245a6c308cbac2f0e03ec49b13b19cbfa852e96`, sequence 0. The separately signed verifier transition retained the existing receipt rather than re-enrolling changed files. First-owner setup was completed through the ordinary pairing-code endpoint for the test.

The original build supported signed-package upload but predated on-Ark package downloads. Its first package therefore used the existing authenticated upload/stage/install API. Preview 1 failed during dashboard regeneration and automatically restored the old software and receipt. The cause was an unprivileged renderer trying to rewrite identical root-published artwork. Immutable-artwork reuse fixed that failure without changing permissions. The corrected preview passed a real recipient-configuration rendering check before another live installation.

`software-2026.11.06-preview.2`, source `fa1cfaaa0acf7aef31cb57cee35fc2fd785d53c7`, completed on the physical Pi and advanced its receipt to sequence 1. Health reported `ok`, no problems and no managed-file drift. The KZ1O notice and installed-only preference remained. The before/after inventory retained all 1,777 library files with unchanged size and modification time; the separate live usage counter changed normally. These are metadata-preservation checks, not a second hash of every content file.

The API, engineering handbook and Kiwix homepage responded successfully. The installed 469 MB FCC database returned the expected callsign search and grid-proximity results with distance and bearing. The update/artwork suite passed 45 isolated tests. The exact package also passed disposable-copy installation and failed-health rollback.

This record distinguishes the verifier transition, original upload path, live automatic rollback and successful bridge installation. Browser automation was unavailable; the authenticated HTTP endpoints used by the page were exercised directly. Subsequent on-Ark acquisition and reboot acceptance are separate checks. No merge was performed.

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
