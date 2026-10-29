# Integration status

## Implemented

Household backup supports SMB, mounted local files/directories and HTTP snapshots, independent maintenance and bug-out policies, private credentials, optional OpenPGP, authenticated triggers/cancellation and event delivery. See [Household bug-out backups](Bugout.md) for configuration and acceptance requirements.

Home Assistant is configured for health/certificate monitoring, bug-out controls and collection/configuration lifecycle events. Installation and tested delivery are documented in [Home Assistant](HomeAssistant.md); integration tokens remain private. No physical-device action or phone push notification is implied by the package.

Manage Library provides installed/pending/removed inventory, storage and activity, password-protected supported downloads/removal/reinstatement, lifecycle diagnostics and public file access. Caretaker caching is optional and tab-scoped. **System → Library** holds the management link. See [Library management](Library.md).

Offline street-map viewing covers all 50 U.S. states and a separate Caribbean archive. Massachusetts flood, parcel and topographic datasets retain their narrower scope. See [Offline references](OfflineReferences.md) and [Local reference maps](Maps.md).

## Remaining work

- Public collection suggestions and storage-sensitive caretaker approval (Send to the Ark).
- Street-map search/routing and browser viewers for additional specialized GIS formats.
- Spare-media and fresh-system recovery acceptance; wider household-source and encryption acceptance.
- UPS/power-budget telemetry, application-specific quiesce/export hooks, hardware/GPIO triggers, shutdown/eject and retention policies.

Configured capability is not an acceptance result. The [acceptance checklist](AcceptanceTests.md) and feature-specific guides identify outstanding tests. No door, light or other physical-device action is configured automatically.
