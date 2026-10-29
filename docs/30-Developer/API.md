# REST API

The API exposes the Ark's status, library, network, configuration, community and household-backup services. Public requests use the `/api` prefix through Apache; the application backend listens on loopback port 8000.

## References

- [API reference](/api/docs): interactive on the Ark and a read-only reference on the public website.
- [Versioned OpenAPI JSON](api/openapi.json): the contract exported with this software edition.
- [Live OpenAPI JSON](/api/openapi.json): the contract served by the running Ark.
- [Status contract](api/status-v1.md).

The generated reference lists every published OpenAPI operation and model. Portal probe routes are intentionally separate; see [AP welcome portal](../20-Administration/Portal.md). Request bodies validated manually by helpers may need the corresponding administration guide as well as the schema.

## Access and authorization

Ordinary reading and public status requests do not require a reader account. Protected operations validate authorization on each request. Caretaker HTTP Basic authorization uses username `admin` and the configured caretaker password; it is separate from the Pi's Linux login and the hotspot name.

The browser can retain caretaker authorization for the requested bounded interval. Caching does not remove server checks or confirmations for destructive operations. The integration token has its own limited household-control scope and does not grant general caretaker access.

## Read a status response

```sh
curl http://dataark/api/status
```

A successful queue response means work was accepted; use the corresponding status and inventory views to follow completion. Installation, activation, removal and restore operations have their own validation and transaction behavior.

## Operating guides

- [Library management](../20-Administration/Library.md)
- [Network and caretaker administration](../20-Administration/AdministratorGuide.md)
- [Configuration](../20-Administration/ModularConfiguration.md)
- [Community board](../20-Administration/CommunityBoard.md)
- [Household bug-out backups](../20-Administration/Bugout.md)
- [Architecture and privilege boundary](Architecture.md)

## Keeping the contract current

The repository is authoritative for the API code and its documentation. Software deployment exports the schema from that source using `venv/bin/python tools/export_openapi.py`, then builds the offline and website references from the same JSON. The public website reference does not execute device-control requests.
