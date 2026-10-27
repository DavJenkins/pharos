# Local usage history

Open [Usage](/usage.html) from System’s Connected devices section. `dataark-usage.timer` runs `tools/collect_usage.py` once a minute. Install or repair with `sudo python3 /opt/dataark/deploy/install_usage.py`. No API restart is needed. New stock-Pi bootstraps install it as well.

The monitor keeps hourly buckets for 30 days and daily buckets for 365 days in `/var/lib/dataark/usage/state.json` (root only), publishing aggregates to `/mnt/storage/usage.json` only while the content drive is mounted. This is appliance activity history, not portable content configuration; new clones begin their own history. Source code and installation configuration travel with the recovery source checkpoint.

Measurements: sampled hotspot station count and daily peak; established SSH, VNC (5900/5901), and browser-terminal (4200) TCP connections; successful Apache document/download GET requests and payload bytes, grouped by collection. TCP connections are not sessions or people. AP samples can miss brief connections. Direct Kiwix on 8080, SMB, FTP and direct-service traffic are outside web statistics.

API/status polling, interface assets, JSON and loopback requests are excluded. No visitor addresses, complete URLs, query strings or user agents are stored by the monitor. Existing Apache logs remain under their own retention policy. Initial activation starts at the end of the current access log, rather than claiming historical coverage. The collector resumes from a durable byte offset and follows standard `access.log` to `access.log.1` rotation. Gaps spanning multiple rotations may lose observations. Reads are limited to 8 MiB per run to bound work; backlog continues on the next run.

Charts use UTC daily buckets and show missing observations as dashes. Check `systemctl status dataark-usage.timer dataark-usage.service` and `journalctl -u dataark-usage.service`. Disable with `sudo systemctl disable --now dataark-usage.timer`; retained aggregates remain available. The monitor does not enable any remote access service or change its permissions.

## Estimated unique visitors

Daily estimated visitors count distinct client addresses making qualifying document GET requests. Polling alone does not count. Shared/NAT addresses undercount, address changes overcount, and daily estimates must not be summed as weekly uniques. No cookies, fingerprinting or persistent visitor identifiers are used. A separate `visitors_started_at` timestamp marks the beginning of this measurement; older unmeasured days show a dash. Today's initial count may cover only part of the day.

The private state keeps HMAC-SHA256 digests with independent random daily salts for up to two days to deduplicate requests across runs and log rotation. Raw addresses are used only in memory. Neither salts nor hashes appear in the public JSON; daily counts remain for one year. A clone starts its own state and salts.
