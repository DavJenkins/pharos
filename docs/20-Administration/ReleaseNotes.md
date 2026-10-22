# Release notes

## October 22, 2026 — library and dashboard work

This is a dated development summary, not a claim of a separately tagged software release. The manifest currently identifies version 1.4 while the API application metadata still reports 1.0.0; do not treat those labels as synchronized release identifiers.

- Added illustrated English iFixit offline content, attribution, publisher hash verification, reader activation, and local landing-page access.
- Hid online-only source cards from the main library; retained source references in management.
- Added Manage Library, linked from the System pop-up, with inventory, free space, full activity, and curated English Gutenberg downloads. Gutenberg is a large optional collection; consult live status rather than assuming it is installed.
- Added password-protected removal and reinstatement of supported archives, including pre-seeded archives. Removal disables automatic re-download and retains source information.
- Added right-aligned trash-can controls, explicit queued/working/completion/error headings, and page-memory caretaker authentication with expiry and manual locking.
- Reworked the nine status controls into Connections, Access and monitoring, and Support tools. Seven open details first; Help and Developer API open directly. Desktop hover text remains.
- Tied portal capture to Debug and added library lifecycle events, durations, bytes, failures and recovery outcomes.
- Corrected public documentation-directory permissions and linked Help directly to the contents page.
- Added anonymous read-only FTP with denied uploads and excluded private/staging paths. SSH/SFTP and account-based rsync remain administrator access methods.

## Remaining work

Public collection requests and storage-based approvals are not implemented. OpenStreetMap offline region/format/reader selection is still planned. GIS data do not yet all have an in-browser map viewer. Full spare-storage recovery, broad client acceptance and some household integration tests remain pending.

## Earlier foundation

The initial API foundation introduced FastAPI, OpenAPI, native Python collectors, service/health reporting and static browser integration. Later manifest, portal, map-maintenance and household-backup changes are described in their administration guides. See the [October 21 project snapshot](ProjectStatus-2026-10-21.md) for historical context; newer behavior above supersedes that snapshot where they differ.
