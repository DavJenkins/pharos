# Project status assessment - 2026-10-21

Verified directly on the Pi with its installed environment; times are Eastern.

## Verified

- All 140 Python regression tests passed in 15.106 seconds. Temporary log: `/tmp/dataark-assessment-tests.log` on the Pi. All four JavaScript suites also passed on the workstation during this assessment session.
- API overall status `ok`, no issues. FastAPI, Apache, Samba, NetworkManager, Kiwix, household worker and portal DNS running. Content and maps timers active; inactive oneshot workers between timer runs are expected.
- Access point active at 192.168.4.1; no clients attached during inspection. Upstream Wi-Fi connected. SSD approximately 181 GiB used, 773 GiB free; root 13% used; CPU approximately 43 C.
- Dashboard, API and Kiwix roots returned HTTP 200. Portable start page, browser and maps index returned 200 under `/library-files/`. Hidden backup/content staging paths returned 404. `/content/START-HERE.html` is not the configured route.
- All source static files match deployed counterparts by SHA-256. Read-only content audit: 329 files, approximately 181 GiB, zero metadata errors. Six ZIM archives present, including old and current WikiMed.
- Maps worker metadata: 174 files, no file/group errors, `Up to date`. Not independently rehashed.
- Manuals snapshots completed October 20 and 21. Latest: October 21 at 00:20, 372,879,360 archive bytes. All 89 regular-file members read (372,793,642 payload bytes); three samples restored to temporary storage and SHA-256 matched against archive streams. Temporary outputs cleaned up. Source equivalence not independently checked.
- Update worker idle. Retained `pending-plan.json` alone does not indicate unfinished activation: worker code overwrites it for activation without deleting afterward.
- Existing Git changes passed `git diff --check`.

## Remaining work

- Branch `feature/readme-foundation` has substantial uncommitted work. Before these documentation edits: 68 tracked files modified and four untracked maps files. Most tracked changes are executable modes; substantive edits totalled 132 added/11 removed lines across seven tracked files. Review modes and preserve maps work in version control before release.
- Controlled offline Android/Apple/Windows tests, two-client forwarding isolation, reboot recovery and physical SSD portability remain unverified. Automated tests do not replace these checks.
- Independent source-to-restore comparison, live encryption and Home Assistant acceptance remain pending. Retention, UPS telemetry, application quiesce/export and safe shutdown/eject policies remain open.
- `x11vnc.service` failed; core Data Ark services healthy. Determine whether remote desktop is required before repairing/disabling it.
- README, release notes and older inventory lag implementation. Corrected stale Manuals setup/deployment information in PlannedIntegrations.md.

Assessment changed documentation only. No production archives, firewall rules, network connections, service state or Git history were changed. No reboot or storage removal performed.
