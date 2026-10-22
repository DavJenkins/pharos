# Developer Guide

## Establish what is actually running

The appliance checkout is /opt/dataark. Inspect its Git branch, status, and content diffs before editing. File-mode-only differences can result from the SMB source share; do not treat them as unfinished feature content or reset unrelated files. The live API is the service registered in app/main.py, not necessarily every similarly named module in the repository.

Inspect systemctl cat dataark.service and the installed helper/service configuration when investigating deployment. The live web root is generated output, not the durable source. Source edits, root-helper installation, static publication, and API restart are separate steps.

## Engineering rules

- Preserve offline reading and honest missing/offline states.
- Validate request bodies at the router and at privileged helper boundaries.
- Accept registered collection identifiers and trusted update series rather than arbitrary URLs or commands.
- Keep credentials out of process arguments, logs, public docs, and version control.
- Use subprocess argument lists rather than shell-built commands for helper operations.
- Keep staging, checksums, locks, rollback journals, and reader validation intact.
- Do not interrupt real transfers or delete real collections to exercise a UI test.

## Change the right source

Dashboard structure belongs in app/templates/index.html; browser behavior and styling belong under app/static/assets. Collection metadata belongs in dataark.yaml. Document public behavior in docs and update the API description when adding routes. Refer to [Architecture](Architecture.md) and [Library management](../20-Administration/Library.md) for component boundaries.

## Verify a change

Run Python checks from the repository using venv/bin/python -m unittest discover -s tests -v. Tests use temporary fixtures and mocks for privileged mutations; inspect a new test before assuming it is safe against the live appliance.

Run JavaScript checks with node --test tests/*.test.js where a compatible Node runtime is available. Node may be run from the development machine against the checkout. A passing mocked test does not prove a real phone's captive portal or an external application's file compatibility.

For a focused change, run the affected suites and meaningful regressions. Exercise actual service startup when modifying a worker entry point: a helper-function test does not catch every startup error. Inspect stderr, service exit status, and updater status rather than relying only on a rendered page.

## Publish

- Preserve the current configuration and review the diff. Do not overwrite a manifest changed by a live content operation.
- Run the relevant tests and a documentation/link build.
- If a fixed-scope helper changed, run its reviewed installer with root privileges. The API must not be granted general-purpose sudo access.
- Run bash deploy/deploy-web.sh from /opt/dataark. It renders the dashboard, builds docs in a fresh directory, and publishes them with public documentation permissions.
- Restart dataark.service for Python API changes. Worker scripts are loaded on their next invocation; do not restart a running transfer casually.
- Verify /api/status, the affected route, Help contents, and the actual browser flow. Reload the browser to load new interface code.
- Commit the intended source/docs/generated dashboard changes and push the established branch. Exclude credentials, captures, downloaded archives, and unrelated file-mode changes.

## Troubleshoot

Use journalctl for the relevant systemd service. Library outcomes and detailed stages are in the common events stream; enable Debug for extra stages. Updater progress and a detailed failure reason are also in /var/lib/dataark/updates/status.json. A queued HTTP response means acceptance, not completion. Record which layer failed: authentication, helper invocation, publisher access, download, verification, reader activation, publication, or cleanup.

Recovery changes require extra care. An uncommitted removal journal should restore the original file/manifest; a committed journal finishes cleanup. Do not manually remove a journal to silence an error. Validate the recovery behavior with disposable fixtures and consult [acceptance tests](../20-Administration/AcceptanceTests.md).
