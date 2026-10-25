# Community board

[Open the board](/community.html). This is a small, local place for announcements, requests, offers, and general discussion. No internet, account, email address, or external service is required. Anyone who can reach the Ark can read posts and replies. Display names are optional and unverified. Messages are plain text; there are no attachments, embeds, private messages, notifications, or Markdown/HTML rendering.

## Posting and removal

Choose New post, a category, a title, and a message. Replies appear beneath the original post. Each successful post or reply returns a random deletion code shown once. Keep it to remove your own message. Codes are not saved in browser storage or returned with public messages. The database stores only their SHA-256 hashes. Losing a code means asking the caretaker for help. Removing the original post removes its replies too; the removal dialog states this before submission.

Every message has a Remove button. Enter its deletion code, or select caretaker moderation and use the existing Ark caretaker password. Caretakers can remove any message. Passwords are held only during the request and cleared when the dialog closes. Rejected codes/passwords leave the conversation unchanged. As elsewhere on the Ark's HTTP interface, this is intended for a trusted local network.

Read access is open. Posting is bounded by per-device and board-wide limits. Default limits are six messages per minute per device, 100 per minute overall, 5,000 total posts/replies, 200 replies per thread, 4,000 characters per message, 120 for titles, and 40 for names. At capacity the board asks the caretaker to clear old conversations; it does not silently expire discussions. Different people behind the same proxy may share a rate limit. Rate-limit identifiers are salted hashes of addresses, kept for approximately one minute; raw addresses are not stored in the board database. Apache may still record its normal access logs.

## Storage and backup

Live SQLite database: `/var/lib/dataark/community/board.sqlite3`, owned by admin, private directory mode 0700 and database mode 0600. WAL journaling and transactions keep concurrent posts consistent. The board is separate from the SSD content catalogue and public HTTP/FTP/SMB file shares. No user messages, credentials, or deletion hashes belong in Git, the public content profile, or the source recovery archive.

`dataark-community-backup.timer` takes an online SQLite snapshot daily, with up to a five-minute scheduling delay. It catches up after downtime. The default seven most recent daily copies are retained in `/var/backups/dataark-community`, private to admin. Repeated runs on the same UTC date replace that day's snapshot. Removing a live post does not erase older backup copies; they age out with retention. `systemctl list-timers dataark-community-backup.timer` shows the actual next run. Run `sudo systemctl start dataark-community-backup.service` to request a snapshot now.

These automatic snapshots are on the **same system card**, so they protect against an application/data mistake, not card failure. Use Download backup on the board and the caretaker password to save an online SQLite snapshot to another device. Keep that downloaded file private: it includes message history and deletion-code hashes. Snapshots are integrity-checked before being published as backups.

To restore: stop `dataark` and the backup timer; preserve the current private database directory; run SQLite `PRAGMA integrity_check` on the chosen backup; replace the database with the verified backup while the service is stopped, removing stale WAL/SHM sidecars only after preserving the old directory; set owner admin:admin and mode 0600; then restart the service and timer. Confirm posts, replies, and author deletion codes. Restoration returns the board to the snapshot's time and may bring back removed messages. No automatic restore is offered. Test restoration on a temporary copy before a real recovery.

## Source, configuration, and installation

Human-readable policy: `/opt/dataark/config/community.json`. Change it locally, then restart dataark. `enabled: false` closes board API access while retaining messages. API routes remain registered but refuse normal reads/writes when disabled. Supported limits have upper safety bounds in the service code. The backup timer fails while disabled; existing snapshots remain. Categories should not be renamed/removed while old posts still use their IDs without a migration.

Install with `sudo python3 /opt/dataark/deploy/install_community.py`, then restart `dataark` and deploy the web interface using `bash /opt/dataark/deploy/deploy-web.sh`. The stock-Pi coordinator includes this installer, but its full spare-Pi acceptance test remains outstanding. No extra Python packages, database server, root helper, or passwordless root permission is needed for normal board operation.

Source: `app/services/community.py`, `app/routers/community.py`, `app/static/community.html`, `app/static/assets/js/community.js`, `tools/backup_community.py`, and `deploy/install_community.py`. [GitHub repository](https://github.com/DavJenkins/pharos). The landing-page link is maintained in `app/templates/index.html`. Tests cover posting, replies, pagination, hashes and code rejection, rate limits, capacity, public-field boundaries, moderation authentication, request size/origin restrictions, and backup/restoration to a temporary database.

The API under `/api/community` is described by the Ark's Developer API. JSON mutation requests and same-origin browser checks prevent unrelated sites from silently posting; all content is inserted into the page as text. The board does not federate or synchronize between Arks. Each Ark is its own community.
