# Household Bugout Backups

Bugout collects configured household SMB directories onto the Ark SSD. It does not require internet or Home Assistant. Local library access stays open; starting a backup or changing share credentials requires the existing administration password. Home Assistant can trigger the same operation with a separate bearer token.

## Configure sources

The installed manifest starts with no tasks. Add actual shares only when you are ready to copy them:

```yaml
bugout:
  reserve_gib: 2
  tasks:
    - id: household-documents
      title: Household documents
      host: nas.home.example
      share: Household
      path: Documents
      credential: household-reader
      priority: 10
      timeout_seconds: 1800
      encryption:
        method: none
    - id: private-records
      title: Private records
      host: nas.home.example
      share: Household
      path: Private
      credential: household-reader
      priority: 20
      timeout_seconds: 1800
      encryption:
        method: openpgp
        public_key: household.asc
```

These are examples, not working addresses. Each SMB task backs up one directory tree; omit path for the whole share. Use separate tasks for independent directories. Credential is a reference, never a password. Omit it for guest access. Disabled tasks (`enabled: false`) are not offered. Lower priority numbers run first; each task has its own timeout. Up to 16 tasks are supported.

Completed snapshots are standard `.tar` files, or OpenPGP-encrypted `.tar.gpg` files, in `/mnt/storage/bugout-backups`. Names contain the task ID and unique operation ID; the UI records the operation time. They can be downloaded from the source's result on the landing page or copied from the SSD. Bugout snapshots and source files are never deleted or overwritten automatically. Normal prefetched copies are replaced atomically after a successful refresh. Manage retention separately. Failed in-process attempts remove only their new partial file. A hard interruption may leave partial files in `.bugout-staging`; they are not published as completed backups.

This is a read-only file snapshot, not a live database backup or a deletion-propagating mirror. Export active databases on their source system first. Changing files can produce an inconsistent snapshot; the Ark cannot quiesce arbitrary remote applications. Tar files are portable and can be inspected/extracted using ordinary archive tools; encrypted files first require the recipient's private key.

## Installation

Run on the Pi from `/opt/dataark`:

```bash
sudo apt install smbclient gnupg curl tar
venv/bin/python -m unittest discover -s tests -v
sudo python3 deploy/install_bugout.py
./deploy/deploy-web.sh
sudo systemctl restart dataark.service
```

The installer creates an independent `dataark-bugout.service` running as admin. It does not start a backup, restart the content updater, modify Wi-Fi, or mount remote shares. Save the printed HA bearer token privately; do not paste it into shared diagnostics. The token is not needed for the landing-page button. Its hash is retained in `/etc/dataark/bugout-ha.json`. Use `--rotate-token` to replace it deliberately. Reinstall only while no bugout operation is active. Existing active worker code is updated by restarting `dataark-bugout.service` after the operation has finished.

The worker needs the existing SSD at `/mnt/storage`; do not change that mount without also updating its systemd sandbox. It reserves two GiB by default, checks space while copying and stops a task if the reserve is reached. Source size is not precomputed, so readiness is not a promise that the entire snapshot will fit. Other sources still get a chance after a task fails.

## Landing page and credentials

No enabled tasks means no bugout panel. The panel shows each configured source and a reason when it is inaccessible. The Bugout button is disabled if no source can run, storage is unavailable, or the worker is unavailable. It also stays disabled throughout an active operation. Internet connectivity is not a requirement. Source reachability is the practical home/away indicator, not an authentication mechanism.

Set credentials beside the relevant source using the existing administration password. **Test credentials** checks a directory listing with the entered username, password and domain before saving. It does not store the credentials, schedule a job, or copy any files; a successful listing does not guarantee read permission on every file. Choose **Save credentials** separately when ready. Remember on this Ark stores them in a private SD-card directory, `/var/lib/dataark/bugout/credentials`, with restrictive permissions. Otherwise they are stored under `/run/dataark-bugout`, expire after one hour, and are removed after the next operation or worker restart. The browser does not save either password in browser storage. Sources with the same credential reference share that credential. Updating credentials is blocked during a queued/running backup. A temporary override can expire back to an existing remembered credential.

Remembered passwords must be recoverable for SMB authentication, so protected storage is not encryption at rest. It is outside the shared SSD and public manifest. Credentials travel to the Ark using the same HTTP administration interface as network settings; use a trusted local network or an appropriately configured HTTPS reverse proxy. All unencrypted snapshots are deliberately readable through the Ark's content access paths.

## Optional OpenPGP encryption

Copy exactly one exported recipient public key to `/etc/dataark/bugout-keys/household.asc`, owned by root, group admin, readable by that group. Only public keys belong on the Ark. Select `method: openpgp` and that filename in the task. The worker streams SMB tar output into GPG; it does not write a plaintext temporary archive to the SSD. It stores only encrypted output for that task. This does not encrypt or remove any earlier plaintext snapshots. Keep the private key elsewhere and verify you can decrypt a small test snapshot before relying on emergency backups.

GPG recipient-file behavior is documented in the [GnuPG manual](https://gnupg.org/documentation/manuals/gnupg26/gpg.1.html). SMB tar collection uses [smbclient](https://devel.samba.org/samba/docs/man/manpages/smbclient.1.html).

## Two-way Home Assistant integration

Home Assistant is optional. Configure outbound reporting interactively on the Pi:

```bash
sudo python3 deploy/install_bugout.py --configure-ha
```

Enter the HA base URL and a long-lived HA access token when prompted; neither goes into the public manifest. Keep HTTPS certificate verification enabled when using HTTPS. The HA server must be reachable from the Pi. Configuration changes are read by the worker without restarting it; the installer refuses changes during an active operation.

HA calls `POST /api/bugout/trigger` with `Authorization: Bearer <Ark integration token>` and JSON `{"operation_id":"a-unique-operation-identifier"}`. Use a UUID or an HA context ID, 16-64 alphanumeric/hyphen/underscore characters. Preserve the same ID for retries. No task paths, credentials, or origin can be supplied by the caller. The Ark assigns origin from authentication: admin is ark, bearer token is home_assistant. HA cannot change share credentials.

The Ark sends authenticated events to HA's `/api/events/dataark_bugout` endpoint with `event_id`, `operation_id`, `origin`, `kind`, `state`, and per-task results. Kinds are trigger, status, completed, and cancelled. Normal maintenance never emits these emergency events. A trigger event is emitted only for a newly accepted operation; status events must never be wired back to the trigger endpoint. A current operation is returned for simultaneous triggers, and each request ID remembers that operation even after it finishes. Replaying a completed request returns its result without copying again.

Delivery uses a persistent ordered retry queue. HA downtime does not cancel or block backup work. The UI reports failed delivery and pending events. Events are delivered at least once: a lost HTTP acknowledgement can lead to a repeated event. HA consumers must deduplicate by event/operation ID. State transitions emit events; detailed byte progress remains available by REST polling. Notifications can be delayed during a long individual copy, since that task has priority over delivery.

See `deploy/home-assistant-bugout.example.yaml` for a package showing both directions without feeding events back into themselves. Customize it before loading in HA. Attach your chosen power/alarm/manual automation to the request script; no power-loss, GPIO, shutdown or USB-eject behavior is enabled automatically. The REST/event transport follows the [HA REST API](https://developers.home-assistant.io/docs/api/rest/) and [RESTful Command integration](https://www.home-assistant.io/integrations/rest_command/).

## Read-only monitoring

`GET /api/bugout/state` reports readiness, each source's reason, the latest operation, byte counts, snapshot links and HA-delivery errors without credentials. `GET /api/status` remains the general system, disk, temperature and content-update status endpoint. HA can poll these without an integration token. Power budget remains unknown until actual UPS telemetry is integrated.

Useful diagnostics:

```bash
systemctl status dataark-bugout.service --no-pager
journalctl -u dataark-bugout.service -n 30 --no-pager
```

Stopping/restarting the bugout worker interrupts any copy. On next start, active operations are marked interrupted, not successful, and are not automatically recopied. Use a new operation ID to retry after inspecting results. Reboot clears use-once credentials but preserves remembered credentials, completed operation IDs and undelivered HA events.

## First live acceptance test

Configure a small disposable source folder, preferably with a dedicated read-only SMB account. Check that missing credentials disable the task, enter credentials, then make one snapshot from the landing page. Open the tar and compare the small test files. Test a bad credential and a disconnected source. For HA, verify one event in each direction, retry the same operation ID, and verify only one archive is created. For encryption, decrypt a small snapshot using the private key on another device. These live checks remain necessary: automated tests use local subprocesses and simulated SMB/HA responses, not your NAS or HA installation.


## Normal sync and bugout are independent

The `bugout.tasks` collection registers household sources for both normal maintenance and emergency collection. Existing Kiwix/reference assets remain under the content update worker; they are not implicitly included in bugout.

```yaml
bugout:
  reserve_gib: 2
  budget_seconds: 300
  tasks:
    - id: manuals
      title: Manuals
      kind: smb
      host: source-host.example
      share: Manuals
      credential: manuals-reader
      prefetch: true
      normal_sync: scheduled
      prefetch_interval: 1d
      include_in_bugout: true
      priority: 100
      timeout_seconds: 3600
      encryption:
        method: none
```

This is an example Manuals source. Replace `source-host.example` and the share name with your source computer and share. Enter that source’s username, domain (if required), and share password in its landing-page credential form. Choose **Remember on this Ark** for unattended prefetch. The worker reads the share directly; `/mnt/manuals` need not be mounted.

- `prefetch: true` permits normal acquisition and refresh; false reserves collection for bugout (if included).
- `normal_sync: manual` runs only through **Sync now** or an explicitly requested cancellation handoff. `scheduled` follows `prefetch_interval`, default `1d`; `365d` is a 365-day interval. `when_available` additionally refreshes when a source becomes reachable again; reachability is sampled every five minutes. This detects source availability, not physical location.
- **Sync now** refreshes reachable sources with `prefetch: true`, including manual sources. It does not include bugout-only sources, start an emergency, or emit HA bugout events.
- `include_in_bugout: false` excludes that source from emergency work. Default true preserves existing household task configurations. A prefetched copy stays available either way.
- `priority` is optional, defaults to 100, and runs lower values first. It does not override deadlines.
- `budget_seconds` defaults to 300 for the whole bugout copy operation. Expiry interrupts the active copy and remaining work. Individual `timeout_seconds` also applies. Readiness checks precede this copy budget, and process cleanup may add a few seconds.
- Optional tasks (`optional: true`) run only with a positive `estimated_seconds` that fits the remaining budget. An unknown or oversized estimate skips the task. Estimates are advisory; the deadline still applies while copying.

Large reference downloads such as Wikipedia should remain outside bugout. If deliberately registered as optional emergency sources, give them low priority (a larger number) and a realistic estimate.

Normal snapshots are full copies, not incremental SMB mirrors. Each source has one current prefetched snapshot per source/encryption configuration; a failed refresh preserves the previous successful copy. Source or encryption configuration changes do not delete old files, but their old cache is no longer presented as current. Normal refresh times are unaffected by a bugout refresh or cancellation handoff. Keep retention of old bugout snapshots and former cache files under separate control.

## Other source types

Local files or directories require an explicit mounted volume. A symlink escaping that mount or a source that includes the backup output is rejected. Directory traversal does not follow symlinks or cross filesystem boundaries.

```yaml
- id: local-documents
  title: Documents on another mounted volume
  kind: local
  mount: /mnt/household
  path: Documents
  prefetch: true
  normal_sync: manual
  include_in_bugout: true
```

HTTP(S) sources represent single files, not a recursive website crawler. Readiness requires a successful HEAD request. Embedded credentials in URLs are rejected; named credential storage currently applies to SMB only.

```yaml
- id: reference-file
  title: Reference file
  kind: http
  url: https://example.org/reference.pdf
  filename: reference.pdf
  prefetch: true
  normal_sync: scheduled
  prefetch_interval: 365d
  include_in_bugout: false
```

SMB/local sources produce `.tar`; HTTP sources preserve the supplied file name/type. OpenPGP can wrap either stream without a plaintext temporary output.

## Cancelling precautionary bugout

The landing page offers **Cancel bugout** and **Cancel bugout and continue updates in background** while a bugout is queued or running. Both require the administration password. HA can also POST `/api/bugout/cancel` with its bearer token and JSON `{"operation_id":"the-operation-id","continue_updates":false}` (or true). Repeated cancellation requests retain the first choice.

Plain cancellation stops remaining work, keeps completed snapshots, and emits a `cancelled` HA event. The second choice queues unfinished sources as normal background maintenance, including normally manual or bugout-only sources explicitly covered by this choice. The continuation emits no HA emergency events. A new bugout takes priority over background copying.

SMB/local tar and encrypted streams restart an unfinished snapshot from the beginning. They cannot safely resume a partial archive. Completed snapshots and source checks are retained. The separate Kiwix content worker retains its existing download-resume behavior; these buttons do not cancel, enroll, or reschedule its jobs.

Scheduled prefetch uses only remembered credentials. Manual sync and its explicit continuation may use unexpired one-time credentials; those expire after one hour and are removed when the operation finishes. If credentials expire before a continuation starts, that source reports an error rather than silently switching access methods.

Cancellation is a status event, not an automatic reversal of external actions. HA may use bugout trigger/status/cancelled events to implement chosen lighting or door automations. No physical actions are configured by the Ark; routine sync must never trigger emergency actions.

After updating worker code, deploy and restart both API and bugout worker while no household copy is active. Do not restart `dataark-update.service` for these changes.


## Forgotten Ark administration password

The administration field uses the separate Data Ark network administration password, not the Windows share password or Pi SSH password. Reset it interactively on the Pi with:

```bash
cd /opt/dataark
sudo python3 deploy/install_network_admin.py --reset-password
```

Enter and confirm a new 12–256 character password. A mismatch or invalid length leaves the existing credential unchanged. The API reads the credential file for each request, so a password reset itself needs no service restart. This password also authorizes the Ark network-settings forms. Share credentials are independent.


## Persistent failure warnings and retry pacing

A reachable source is not proof of a successful backup. The household panel keeps a prominent warning after failed, unavailable or interrupted prefetch attempts, including the failure count and earliest next automatic attempt. A previous successful copy remains downloadable when present. Missing saved copies also produce a warning. A later successful refresh clears the copy-failure warning.

Repeated normal-refresh failures wait 5, 10, 20, 40, 80, 160 and 320 minutes, then at most six hours between attempts. Success resets the failure count and restores the configured interval. Legacy failure records start with a five-minute delay. Manual Sync now bypasses automatic backoff; saving remembered credentials also makes the source eligible for an immediate retry. Reconnection-triggered sources may retry when availability returns. Background continuation preserves the pre-existing normal schedule and its backoff.

These changes require deploying the web assets and restarting the API and household worker when idle. They do not require restarting the reference-content updater.
