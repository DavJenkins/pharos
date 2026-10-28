# Content types and handler API v1

## Purpose and current scope

`config/content-types.yaml` is the single registry for restoration types. Handlers
shipped with the Ark and handlers added later use exactly the same declaration,
loader, context and result contract. There is no native/plugin flag or alternate
execution path. Python supplies mechanisms; configuration chooses a handler and
its options. This interface currently integrates the restoration queue, not every
scheduled updater or content-management endpoint.

The existing collection installers are reached through a compatibility adapter.
Their collection-specific internals have not all been converted to configuration.
They advertise only `restore`; do not infer support for removal or standalone
verification. File downloads use the established resumable, verified downloader.
The queue retains its existing reader publication steps after archive restoration.

## Register a type

```yaml
schema: 1
types:
  example-text:
    api: 1
    handler: plugins/example_text.py
    operations: [restore, inspect, verify]
    options: {}
```

The file is UTF-8 YAML. All four fields are required. Unknown fields, duplicate
keys, unsupported versions and unknown operations are rejected. `handler` names
an existing `.py` file inside the trusted source repository; absolute paths,
traversal and symlink escapes are rejected. `options` is a mapping whose fields
and defaults the handler documents and validates. No shell command strings or
inline Python are evaluated from YAML.

Reference a registered type in `config/content/content.yaml`:

```yaml
recipes:
  - id: local-welcome
    type: example-text
    enabled: true
    path: welcome.txt
    text: Welcome to the Data Ark
    installed_bytes: 4096
    temporary_bytes: 4096
    update_headroom_bytes: 4096
```

`id` uniquely identifies the collection; `type` identifies its handler. Older
recipes without `type` use their `id` as the type name. Existing file groups
`archives`, `direct_files` and `map_files` select those registered type names.
Capacity estimates are bytes, conservative and caretaker-reviewed. Unknown bounds
block queue approval. `requires` lists collection IDs, not type names; the queue
orders dependencies and detects missing/cyclic dependencies.

## Python interface

Each module declares `API_VERSION = 1` and implements:

```python
def validate(item, context):
    # Raise ValueError for invalid fields. No downloads or writes here.
    ...

def restore(item, context):
    ...
    return {"status": "complete", "message": "Installed and verified"}
```

Every declared operation takes `(item, context)`; `validate` runs first on every
dispatch. `item` is the collection mapping from the reviewed recipe. Do not mutate
it or `context.profile`. Context fields:

| Field/method | Meaning |
| --- | --- |
| `content_root` | Destination drive as a `Path` |
| `profile` | Reviewed restoration profile, including reserve/rate settings |
| `profile_folder` | Directory containing the recipe and portable snapshots |
| `options` | A copy of this type's registry options |
| `target(relative)` | Resolve a relative content path; reject escapes |
| `checkpoint(phase)` | Check cooperative cancellation, then emit a short phase |
| `progress(phase)` | Progress callback; prefer `checkpoint` |
| `cancelled()` | Whether cooperative cancellation is requested |

The existing queue also stops the worker process group on pause/cancel and records
interruption persistently. Legacy recipe adapters currently report coarse phases;
they do not promise fine-grained progress or cooperative cancellation internally.
Do not daemonize children or escape that process group.

## Operations and results

| Operation | Required behavior |
| --- | --- |
| `restore` | Reuse verified existing content; otherwise acquire, verify, then publish |
| `inspect` | Read-only presence/state inspection |
| `verify` | Read-only integrity checks; raise on corruption |
| `update` | Apply the configured source/edition policy, preserving the previous usable copy until verified |
| `remove` | Remove only owned collection files; retain desired-state/source information for reinstatement |

Declare only operations actually implemented. Unsupported operations fail before
the handler is imported. No UI removal endpoint is automatically exposed by adding
`remove`. Caretaker authorization and confirmation belong to the calling service.

Return a dictionary with `status` (`complete`, `present`, or `missing`) and a
human-readable `message`. `missing` is useful for inspection; it fails mutating
operations rather than marking a failed install complete. Additional result fields
may be supplied but are not currently consumed by the queue. Raise `ValueError`
for invalid configuration/integrity, `RuntimeError` for operational failure, or
`InterruptedError` for cooperative cancellation. The queue records failure and
keeps the job resumable. Do not log passwords, tokens or private file contents.

## Reliability and dependencies

Handlers must be idempotent: repeating work after an interruption must not damage
existing content. Download to staging, enforce capacity/rate limits, check sizes,
hashes and format, then atomically publish on the same filesystem. Never replace
the only usable copy before verification. Resume safely or restart staging work;
document which behavior is supported. Cleanly report missing executables or Python
packages. This version does not install dependencies automatically: document and
provision them during appliance setup, using pinned/reviewed versions as practical.
The example uses only the standard library.

Use the existing shared content lock; handlers must not acquire a conflicting
second lock or circumvent the queue's capacity checks. Lifecycle hooks run with
the worker's permissions, potentially root. This is not a Python sandbox.

## Trust, portability and recovery

Installing or editing handler code is caretaker/local-administrator work. The web
public-manifest editor does not upload Python or edit this executable registry.
Inspect source before approving a queue. Registry reads validate structure without
importing modules; loading a Python module executes its top-level statements.

Portable configuration bundles include the registry and every declared handler
file. Queue fingerprints include their bytes: changing either invalidates an
existing approval. Keep helper modules/dependencies with the matching source
repository; arbitrary dependency trees are not discovered or bundled automatically.
Never put secrets in handler options or portable files. These additions do not
make recovery dependable until spare-media acceptance tests pass.

## Conformance and example

From the source repository, using the Ark Python environment:

```sh
python tools/check_content_types.py
python -m unittest tests.test_content_types
```

The checker imports reviewed modules and checks API versions and callable
signatures. It does not invoke lifecycle operations and cannot establish safety,
correctness or dependency availability. The tests exercise `plugins/example_text.py`
in a temporary directory, including restore/reuse, verification, cancellation and
invalid inputs. Use that file as a working template, not as proof that an arbitrary
new handler is correct. Add fixture tests for failures, interrupted acquisition,
capacity exhaustion and source changes; then test on spare media.

An incompatible contract change requires a new API version and explicit migration.
Do not silently reinterpret an existing version's inputs or results.
