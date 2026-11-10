# First-owner setup security and offline alerts

The four-digit setup code protects initial network-browser enrollment. It is not online activation or a licence. A trusted local installer or Docker host terminal can set the owner credentials directly; no extra code step is required afterward. If first-owner browser setup is deferred, distribute a fresh private code with that device. Cloning must not reuse the original owner's code or credentials.

## Immediate local reporting

Incorrect setup codes and requests during the resulting cooldown are recorded as rejected attempts, not confirmed compromises. Successful first-owner setup is also recorded. The record contains event identity, kind, original UTC time, occurrence count and delivery/acknowledgement state. Submitted codes and passwords are never included. Repeated cooldown requests are grouped into one event per minute.

Unacknowledged failed attempts appear in System health and link to **Setup security**. A caretaker can acknowledge the displayed attempts; acknowledgement does not cancel queued delivery. An unclaimed offline appliance cannot notify a remote service before it has connectivity and a configured integration.

## Home Assistant and offline retention

With outbound Home Assistant integration configured, each new setup-security event is offered for immediate delivery. The Ark sends the `dataark_setup_security` event and creates or updates a persistent notification for that Ark. Original event time and a stable event ID travel with retries; consumers can use the ID to suppress duplicates after a lost acknowledgement.

Alternatively install `deploy/home-assistant-setup-security.example.yaml` alongside the existing HA bugout package, replace `http://dataark` with the reachable Ark address, and retain the existing private `dataark_authorization` secret. This receiver polls every five seconds and drains cached alerts in batches of up to 100. It creates a persistent notification and logbook entry, fires the same stable event, then acknowledges delivery using the limited integration token. It does not clear caretaker warnings. This path requires no long-lived HA token on the Ark. Validate the HA configuration and restart/reload the REST integration after adding the package.

Undelivered setup alerts survive process restarts and reboots in `/var/lib/dataark/bugout/setup-security/events.sqlite3`. They are retried by the bugout worker when Home Assistant is available, with backoff capped at five minutes. Both configured-but-offline and not-yet-configured integrations retain messages. Events expire after **30 days**; a bounded journal retains at most 1,000 setup events. Expired alerts are not reported later as new events. Local health remains amber until failed attempts are acknowledged or expire.

The bugout event outbox also retains events without a currently configured destination, for up to 30 days, preserving their lifecycle order. Collection/software lifecycle events remain available through their separate bounded local feed for Home Assistant polling.

## Endpoints and operations

- `GET /api/recipient/security`: bounded setup-event summary and whether outbound reporting is configured. It exposes no codes, passwords, tokens or caller addresses.
- `POST /api/recipient/security/acknowledge`: caretaker-authorized acknowledgement of displayed event IDs.
- `POST /api/recipient/security/delivered`: integration-token acknowledgement of receipt, without permission to clear local caretaker warnings.
- `GET /api/health`: includes outstanding setup attempts in the appliance health problems.

The worker must be active for background retries. Root-owned enrollment code also logs rejected setup codes to the local system journal. Reporting failure must never authorize enrollment or change credentials. Review the private Home Assistant integration settings if local alerts remain pending while the HA instance is reachable.
