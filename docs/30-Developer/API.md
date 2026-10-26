# REST API

## Entry points

Public browser requests use the /api prefix through Apache. The backend itself listens on 127.0.0.1:8000. For example, /api/status on Apache corresponds to /status on the backend. Keep that distinction when reading access logs or writing local probes.

- [Interactive API documentation](/api/docs)
- [OpenAPI schema](/api/openapi.json)
- [Status contract](api/status-v1.md)

The route list below was checked against the live schema and portal source on October 22, 2026. The live OpenAPI schema is authoritative for current published request/response shapes. Portal routes intentionally do not appear in that schema.

## Public read-only routes

- GET /api/ returns the application identity/version.
- GET /api/about returns appliance information.
- GET /api/status returns network, system, resources, monitored services, health, sync and updater state. Unavailable telemetry is not silently converted into a healthy value.
- GET /api/network returns the network view.
- GET /api/events?limit=100 returns recent common events; limit is bounded from 1 to 1000. This is not the separate portal packet capture.
- GET /api/debug returns whether Debug is enabled.
- GET /api/library returns installed, pending, and removed registrations, storage and progress. Inventory is primarily a manifest/filesystem view, not a full viewer validation.
- GET /api/library/catalogue fetches supported download metadata from the publisher; it can fail when upstream is unavailable.
- GET /api/bugout/state returns configured household-source readiness and operation state.

## Library mutations

All library POST routes require HTTP Basic administration authentication, using username admin and the configured shared caretaker password. Do not infer the password from the username. The UI retains successful authentication only in page memory and still confirms destructive operations.

- POST /api/library/unlock checks authentication without starting a content operation.
- POST /api/library/install accepts repository_id, release, and bytes from the curated catalogue.
- POST /api/library/remove accepts asset_id, relative_path, and bytes identifying the reviewed installed file. The helper revalidates them; caller-supplied arbitrary paths cannot be removed.
- POST /api/library/restore accepts asset_id for a retained removed record with a supported source.

Mutation bodies use JSON and have bounded sizes. Successful install/reinstate responses queue background work; use inventory/updater status to establish completion. Removal waits for its transaction. Invalid passwords produce 401; validation and helper failures normally produce 400. Lock conflicts currently surface as helper validation errors rather than a promise that the request has been queued.

## Network administration

POST /api/network/admin/{action} accepts scan, connect, or rename only. It requires the shared administration authentication and a bounded JSON body. The installed helper restricts scan/connect to the upstream interface and rename to the hotspot profile. See [Administrator Guide](../20-Administration/AdministratorGuide.md) before operating remotely.

## Household backup commands

POST /api/bugout/trigger starts a server-configured operation. POST /api/bugout/sync requests prefetch maintenance. POST /api/bugout/cancel changes the operation state. Trigger/cancel may accept a separately configured Home Assistant integration token; administrator-only operations require the caretaker credential.

POST /api/bugout/credentials/{task_id} saves private source credentials and POST /api/bugout/credentials/{task_id}/test tests them without storing/copying as described in the [household guide](../20-Administration/Bugout.md). Do not log these bodies or confuse them with public library downloads.

## Portal routes

- GET /api/portal/upstream checks the Ark's upstream internet, independently of the caller's pass-through permission.
- GET /api/portal/state returns state for a verified hotspot peer.
- POST /api/portal/pass-through/on and /off change forwarding for that peer. The compatibility /continue route enables it.
- GET and HEAD /api/portal/probe/{name} implement known operating-system discovery probes.

Mutating portal routes require the expected local origin and an Apache-supplied hotspot peer address. They are not general authenticated administration routes. Do not expose the backend directly or trust arbitrary forwarded headers.

## Debug control and limitations

POST /api/debug/on and /off currently toggle diagnostics without the caretaker gate. This is an existing local-network control, not a model to copy for library deletion. The portal monitor follows that flag; library outcomes are always recorded while detailed stages follow Debug.

The local HTTP API is not transport-encrypted. Keep credential use within the intended trusted local deployment. Error messages are user-facing, but logs are needed to distinguish acceptance from downstream activation and recovery.


## Offline documentation presentation

The interactive reference at `/api/docs` and handbook at `/docs/SUMMARY.html`
share the DEJ masthead, blue/gold palette and cream reading surface. The common
frame is `app/services/documentation_theme.py`; its stylesheet is
`app/static/assets/css/ark-documentation.css`. Handbook pages are generated by
`tools/publish_docs.py`; the interactive route is `app/routers/documentation.py`.

Swagger UI 5.34.0 is preserved in `app/static/assets/vendor/swagger-ui` with its
Apache-2.0 LICENSE, NOTICE and source/integrity record. JavaScript, CSS, favicon,
font and OpenAPI schema are served locally. No CDN is required, the external
schema validator is disabled, and authorization is not persisted across reloads.
`tools/vendor_api_docs.py` can reproduce the pinned assets with SHA-512 package
verification. `/api/redoc` redirects to the themed interactive reference. Existing
endpoint authorization and access controls are unchanged.
