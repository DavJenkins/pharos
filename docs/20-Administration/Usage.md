# Local usage history

Open [Usage](/usage.html) from System’s Connected devices section. `dataark-usage.timer` runs `tools/collect_usage.py` once a minute. Install or repair with `sudo python3 /opt/dataark/deploy/install_usage.py`. No API restart is needed. New stock-Pi bootstraps install it as well.

The monitor keeps hourly buckets for 30 days and daily buckets for 365 days in `/var/lib/dataark/usage/state.json` (root only), publishing aggregates to `/mnt/storage/usage.json` only while the content drive is mounted. This is appliance activity history, not portable content configuration; new clones begin their own history. Source code and installation configuration travel with the recovery source checkpoint.

Measurements: sampled hotspot station count and daily peak; established SSH, VNC (5900/5901), and browser-terminal (4200) TCP connections; successful Apache document/download GET requests and payload bytes, grouped by collection. TCP connections are not sessions or people. AP samples can miss brief connections. Direct Kiwix on 8080, SMB, FTP and direct-service traffic are outside web statistics.

API/status polling, interface assets, JSON and loopback requests are excluded. No visitor addresses, complete URLs, query strings or user agents are stored by the monitor. Existing Apache logs remain under their own retention policy. Initial activation starts at the end of the current access log, rather than claiming historical coverage. The collector resumes from a durable byte offset and follows standard `access.log` to `access.log.1` rotation. Gaps spanning multiple rotations may lose observations. Reads are limited to 8 MiB per run to bound work; backlog continues on the next run.

Charts use UTC daily buckets and show missing observations as dashes. Check `systemctl status dataark-usage.timer dataark-usage.service` and `journalctl -u dataark-usage.service`. Disable with `sudo systemctl disable --now dataark-usage.timer`; retained aggregates remain available. The monitor does not enable any remote access service or change its permissions.

## Estimated unique visitors

Daily estimated visitors count distinct client addresses making qualifying document GET requests. Polling alone does not count. Shared/NAT addresses undercount, address changes overcount, and daily estimates must not be summed as weekly uniques. No cookies, fingerprinting or persistent visitor identifiers are used. A separate `visitors_started_at` timestamp marks the beginning of this measurement; older unmeasured days show a dash. Today's initial count may cover only part of the day.

The private state keeps HMAC-SHA256 digests with independent random daily salts for up to two days to deduplicate requests across runs and log rotation. Raw addresses are used only in memory. Neither salts nor hashes appear in the public JSON; daily counts remain for one year. A clone starts its own state and salts.

## All-time estimate

A separate HyperLogLog sketch with 16,384 registers deduplicates client addresses across days, using a persistent random HMAC-SHA256 salt. Neither this salt nor the sketch registers are published. The sketch needs fixed storage, cannot enumerate visitors, and survives collector restarts. Its nominal relative standard error is about 0.81%; shared addresses and address changes add uncertainty that this bound does not cover.

`all_time.started_at` records when this estimate began. It is not a sum of daily counts and is not backfilled from old logs. The current figure appears in System and Usage. The private state retains the all-time salt and sketch indefinitely, while daily deduplication hashes still expire after two days. Retain `/var/lib/dataark/usage/state.json` in a private appliance backup to preserve continuity; new clones start their own usage history. Only the estimate, start date and statistical error are public.

## Page views versus file downloads

Page views (including landing-page refreshes) and file downloads have separate counters. Visitor estimates include qualifying page views, but page views never increment downloads. File requests such as PDFs, EPUBs and ZIPs count when successfully served, whether viewed or saved by the browser. Repeated requests are separate file deliveries, not unique documents or proof of a completed save. `download_counting_started_at` records when the split counters began; older request totals remain unchanged.
