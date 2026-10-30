# Preview release audit — October 30, 2026

The refreshed preview is built from source revision `bbf93a1ea05c37df8879aaa7c1a6079cd05a2cb2` on `feature/readme-foundation`. The normal web deployment script completed inside a private mount namespace, with its output redirected to a staging web root and the library mounted read-only. The live site was not replaced by this test.

| Check | Result |
| --- | --- |
| Local landing-page links and required assets | 1,497 checked; no failures |
| Kiwix archive entry pages | All 8 served actual content |
| Reader resources | Representative local CSS, JavaScript and images served; Gutenberg’s required CSS/JavaScript and normal favicon served |
| Caretaker boundaries | 11 anonymous mutation requests rejected with HTTP 401 |
| Focused Python regressions | 105 passed |
| JavaScript regressions | Backup interactions, public polling and compact health states passed |
| Deployment persistence | Capture status styling, webpage reviews, library contrast, compact notices, maker/sign links and grouped backup actions retained |

Gutenberg’s supplied archive references two absent favicon PNGs. Its normal favicon and required reader resources work. The original archive is unchanged.

The Python regression run preceded a test-only JavaScript fixture adjustment; the Python executable sources were unchanged. The final committed revision was used for the last deployment replay and the kit. The kit includes `RELEASE-VALIDATION.json`, source identity and checksums. Publisher links are external references and are not counted among the local HTTP passes.

This audit covers deployment, serving and authentication boundaries. Earlier clean-system bootstrap and paired-recovery evidence remain separate; physical spare-media acceptance is still required before calling recovery dependable. No merge was performed.

[Release and bootstrap guide](../00-Introduction/BootstrapDownload.md) · [Engineering](../30-Developer/Engineering.md)
