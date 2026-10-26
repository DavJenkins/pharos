# Home Assistant integration

The Ark remains usable without Home Assistant or an internet connection. Home Assistant is an optional local supervisor: it can display health, record changes, notify people, and run caretaker-selected responses.

Install `deploy/home-assistant-bugout.example.yaml` as a Home Assistant package, customize every `http://dataark` URL to an address reachable from the HA host, and configure the integration token using the existing bugout installer. The source repository is `/opt/dataark` on the Ark and https://github.com/DavJenkins/pharos on GitHub. Integration credentials belong on each system's private storage, never in the downloadable seed or content profile. Reload/restart Home Assistant and verify the entities before relying on them.

## Health reporting

`GET /api/health` is read-only, requires no password, and returns no credentials. It reports overall state (`ok`, `warning`, `error`), stable problem identifiers, severity, human-readable messages, and a fingerprint that changes when the problem set changes. Observation timestamps alone do not change the fingerprint.

Checks cover resource thresholds and core services, failed systemd units, content/map update failures, publisher-check failures and pending source changes, and optional HTTPS setup and certificate health. Certificate renewal warns within 30 days; expiry is an error. HTTPS not configured is normal. Source-check failures do not imply saved content is unusable. This is monitored coverage, not proof that every possible hardware, content, or network fault can be detected.

The package polls health every 30 seconds. It exposes the full problems list and certificate data, a problem binary sensor, and certificate days remaining. A change creates or updates one persistent notification and writes a logbook entry, then fires `dataark_health_changed` for your own automations. Recovery dismisses the notification. An unreachable API marks the sensor unavailable; a separate automation reports loss of contact after two minutes. HA's recorder retains these entities unless your recorder configuration excludes them. No automatic reboot, shutdown, network changes, or content removal is configured.

## Bug-out in both directions

HA can call the authenticated `/api/bugout/trigger` endpoint through `script.request_dataark_bugout`. Retries must reuse the operation ID; the Ark deduplicates requests and validates readiness. Cancellation has its own authenticated endpoint. The token permits bug-out commands, not arbitrary administration.

When outbound HA event delivery is configured, Ark-originated runs emit `dataark_bugout` events. The package converts a new Ark trigger into `household_bugout`, without calling the Ark again. Completion and failure events remain available for HA automations. The separate bugout sensor exposes readiness, tasks, operation status and delivery problems. Subscribe your household actions to these events; test with harmless actions before assigning real emergency responses. A disconnected HA cannot receive live events until connectivity returns.

## Acceptance checks

Confirm the health URL works from HA; confirm certificate and problem entities; check an ordinary health change produces one notification rather than a notification every poll; verify recovery and unavailable handling. Test both bug-out directions with a safe test task and verify no trigger loop. Keep HTTP available for recovery even when optional HTTPS is enabled.
