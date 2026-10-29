# Home Assistant integration

The Ark remains usable without Home Assistant or an internet connection. Home Assistant is an optional local supervisor: it can display health, record changes, notify people, and run caretaker-selected responses.

Install `deploy/home-assistant-bugout.example.yaml` as a Home Assistant package, customize every `http://dataark` URL to an address reachable from the HA host, and configure the integration token using the existing bugout installer. The source repository is `/opt/dataark` on the Ark and https://github.com/DavJenkins/pharos on GitHub. Integration credentials belong on each system's private storage, never in the downloadable seed or content profile. Reload/restart Home Assistant and verify the entities before relying on them.

## Health reporting

`GET /api/health` is read-only, requires no password, and returns no credentials. It reports overall state (`ok`, `warning`, `error`), stable problem identifiers, severity, human-readable messages, and a fingerprint that changes when the problem set changes. Observation timestamps alone do not change the fingerprint.

Checks cover resource thresholds and core services, failed systemd units, content/map update failures, publisher-check failures and pending source changes, and optional HTTPS setup and certificate health. Certificate renewal warns within 30 days; expiry is an error. HTTPS not configured is normal. Source-check failures do not imply saved content is unusable. This is monitored coverage, not proof that every possible hardware, content, or network fault can be detected.

The package polls health every 30 seconds. It exposes the full problems list and certificate data, a problem binary sensor, and certificate days remaining. A change creates or updates one persistent notification and writes a logbook entry, then fires `dataark_health_changed` for your own automations. Recovery dismisses the notification. An unreachable API marks the sensor unavailable; a separate automation reports loss of contact after two minutes. HA's recorder retains these entities unless your recorder configuration excludes them. No automatic reboot, shutdown, network changes, or content removal is configured.

## Bug-out in both directions

HA can call the authenticated `/api/bugout/trigger` endpoint through `script.request_dataark_bugout`. Retries must reuse the operation ID; the Ark deduplicates requests and validates readiness. Cancellation has its own authenticated endpoint. The token permits bug-out commands, not arbitrary administration.

When outbound HA event delivery is configured, Ark-originated runs emit `dataark_bugout` events. The package converts a new Ark trigger into `household_bugout`, without calling the Ark again. The package also polls for recent Ark-originated runs and deduplicates them by operation ID, so an HA long-lived token is not required for this direction. Polling accepts recent operations only and never starts another Ark run. Completion and failure events remain available for HA automations. The separate bugout sensor exposes readiness, tasks, operation status and delivery problems. Subscribe your household actions to these events; test with harmless actions before assigning real emergency responses. A disconnected HA cannot receive live events until connectivity returns.

## Acceptance checks

### Collection and configuration changes

Install `deploy/home-assistant-collections.example.yaml` alongside the existing
package, as `/config/packages/dataark_collections.yaml` (underscores: HA rejects
hyphens in package names even when its general configuration check passes). Change `http://dataark`
to the address reachable from HA. This adds read-only polling, not a new credential
or a broader inbound-control permission. Check HA configuration and restart HA to
load the new REST integration and helper. Existing bug-out settings remain intact.
On the Ark, initialize the shared journal with
`sudo /opt/dataark/venv/bin/python /opt/dataark/deploy/install_collection_changes.py`
and restart the API after installing the source changes. The automatic-update
installer also initializes this journal on a fresh setup.

The package polls `/api/library/changes` every ten seconds. The Ark keeps a SQLite
journal at `/var/lib/dataark/collection-changes/changes.sqlite3`, retaining 1,000
lifecycle events. The API returns the latest 200, in sequence order, plus current
updater activity. Percentage updates replace activity and do not create events.
Both recording and HA polling work with Debug off. An idle updater is not treated
as proof of successful installation; archive activation emits `installed` only
after successful activation.

HA exposes `sensor.data_ark_collection_changes` and
`sensor.data_ark_collection_activity` (collection, percent and timestamp attributes).
It fires `dataark_collection_changed`, records lifecycle changes in the logbook,
and uses one replaceable persistent notification for outcomes needing attention
or successful installation/configuration publication. Phone push notifications
are not configured automatically; attach your preferred HA notification action
to the event. No household power, network or emergency action is attached.
The raw journal sensor is excluded from Recorder to avoid repeatedly storing its
entire retained event list. The compact activity sensor and logbook records remain
available for history unless excluded by your own Recorder settings.

Event fields: `event_id`, `sequence`, `kind`, `collection_id`, `title`,
`operation_id`, `action`, UTC `timestamp`, and optional `error_type`/`percent`.
Errors expose a class/category, not arbitrary exception text; consult Ark diagnostics
for detailed context. Payloads contain no source URLs, credentials, client identity,
configuration bodies or browsing history. Library titles remain visible to local
clients, like the public library itself.

Current producers cover authenticated library requests, queue approval, removals,
updater phases/failure, successful archive activation, and configuration
queue/publication/failure. The journal API also accepts internal `suggested`,
`approved`, `rejected` and `cancelled` events for the planned Send to the Ark
workflow. That browser submission/approval workflow is not implemented by this
HA package, and no pending-request count is fabricated from event history.

The persistent `input_text.dataark_collection_cursor` avoids replay on every poll
and permits catching up after a disconnection, within the returned history window.
It advances after each processed event. Delivery is at least once: a crash between
firing an event and saving the cursor can repeat it; consumers performing actions
must deduplicate `event_id`. A journal replacement resets the namespace. When a
nonzero cursor falls behind the available window, HA emits
`dataark_collection_feed_gap` and raises a notification rather than pretending
the history is complete. The journal is runtime state, not a portable public
configuration or a guaranteed long-term audit archive.

Verify a harmless configuration publication or normal library operation creates
one lifecycle event, while percentage updates only change the activity entity.
Restart HA and confirm previously processed events are not replayed. Test a
disconnect/reconnect and inspect the cursor. Keep failure notifications and any
downstream actions independent of the Ark's ability to contact HA.

Confirm the health URL works from HA; confirm certificate and problem entities; check an ordinary health change produces one notification rather than a notification every poll; verify recovery and unavailable handling. Test both bug-out directions with a safe test task and verify no trigger loop. Keep HTTP available for recovery even when optional HTTPS is enabled.

## Current installation

Installed on `http://homeassistant.local:8123` using `/config/packages/dataark.yaml`, with the package include in `/config/configuration.yaml`. A pre-change configuration backup is `/config/configuration.yaml.before-dataark-20261025`. The private authorization scalar is `/config/dataark-authorization.yaml`, mode 0600, referenced by the package; it is excluded from public source. The Ark holds only its SHA-256 verifier in `/etc/dataark/bugout-ha.json` (root:admin, 0640). Replacing that token invalidates old token clients without changing caretaker access.

Configure the package with a hostname or address that your Home Assistant instance can use to reach the Ark. Update that setting if the Ark’s address changes. The Data Ark dashboard is `/data-ark/overview` and its source is `/config/dataark-dashboard.yaml`. A source example is `deploy/home-assistant-dashboard.example.yaml`. Household actions remain unassigned: owners subscribe their chosen actions to `household_bugout` or `dataark_health_changed`. The dashboard's bug-out button asks for confirmation.

Validation included HA's own `ha core check`, successful authenticated input validation (400 for an intentionally empty request, rather than 401), and live sensor/dashboard checks. No actual emergency operation was started by that authentication check.


### Collection notification deployment — October 28, 2026

The separate collection package is installed at
`/config/packages/dataark_collections.yaml`, alongside the original bug-out/health
package. The dashboard includes Library activity and Current collection cards.
The pre-change dashboard is `/config/dataark-dashboard.before-collections.yaml`;
a package backup before the final event-payload correction is
`/config/dataark-collections.before-payload-fix.yaml`.

Live acceptance confirmed HTTP 200 from `/api/library/changes`, both HA collection
entities, and delivery of a clearly labeled integration-test notification without
changing content. The source regression suite passed 46 tests, followed by 12
journal/package tests including the added HA event-payload schema regression.
HA's general configuration check alone did not catch an invalid package slug or
whole-dictionary event template; actual startup logs and the delivered notification
were checked. Event actions must use explicit mappings for `event_data`.

The API restart cleared its shutdown timeouts without rebooting the Pi. The
pre-install source backup is `/var/backups/dataark-ha-collections-20261028T160727Z`.
Existing publisher-check warnings are independent of the notification integration.
The Send to the Ark submission interface remains separate future work.
