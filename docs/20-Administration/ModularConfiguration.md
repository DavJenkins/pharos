# Modular public configuration

The public content manifest is split into readable authoring files under
`/opt/dataark/config/library`. The main `ark.yaml` is about 13 KB/427 lines for
the current collection, rather than the combined manifest's approximately
1.1 MB/20,700 lines. Detailed publication definitions still exist; they are not
thrown away or inferred from the content drive.

| File | Purpose |
| --- | --- |
| `ark.yaml` | Main public settings, personalization, categories, dashboard grouping and ordered collection references |
| `collections/<id>.yaml` | One repository/collection definition, links, artwork, policy and catalogue/snapshot references |
| `catalogues/<id>.yaml` | Detailed desired asset definitions: titles, sources, paths, policy and metadata |
| `state/versions/<id>.yaml` | Generated known checksum snapshot, used for reproducible versions |
| `state/order.yaml` | Generated compatibility ordering across collections |
| `.layout.json` | Synchronization hashes to detect manual edits before replacing files |

The shared handler registry remains `config/content-types.yaml`, referenced from
`ark.yaml`; it is not duplicated as a second registry. Handler source and its
interface are documented in [Content handlers](ContentHandlers.md).

These `state/` files record version/order information, not desired selections.
Actual installed files, download progress and runtime health still come from the
SSD and the existing runtime services under `/var/lib/dataark`. A missing or empty
drive does not disable collections or erase their definitions. A removed asset's
explicit configuration remains distinct from its absence on disk.

## Web editor

Open **Settings → System → Configuration… → Load configuration**. The editor opens
`ark.yaml` first. **Configuration file** opens a folder tree: expand folders individually and select a file. The filename stays above the editor; unsaved changes are marked. **Section** rebuilds for each file, preselecting and disabling a single available section. Old text clears immediately while another file loads. Technical help and full-snapshot **History** are collapsed disclosures.
Generated `state/` files can be inspected and downloaded but are read-only.
The advanced combined compatibility snapshot remains available.

Reading, downloading, switching files and validating drafts require no caretaker
password. **Save & publish** and the Community switch still require authorization.
Saving one file assembles and validates the complete public configuration, preserves
private household settings, writes the combined compatibility view, republishes
the landing page and refreshes modular files. Unchanged files keep their comments;
the edited file keeps its submitted text when it represents the validated result.
No content is downloaded or deleted by the publisher itself.

The existing history stores complete public snapshots. Loading history selects
the combined view, so restoring a previous version restores the whole previous
public configuration rather than accidentally mixing old and new collection files.
Publication uses revision checks, the existing updater lock and root-only backups.
The previous main manifest and public profile are preserved, and the prior modular
texts are backed up as `<job-id>.project.json` in `/var/backups/dataark-configuration`.
Handled publication/write failures roll back touched files. Power-loss and spare-
media recovery acceptance tests remain required; this is not a claim of dependable
recovery under every interruption.

## Editing files locally

Collection, catalogue and version references are relative to the project directory.
The fixed type-registry reference is repository-relative. Paths cannot escape it;
YAML must have unique string keys and no executable tags. Missing references,
duplicate asset IDs, mismatched repository IDs and oversized/recursive documents
are rejected. Catalogue ordering is respected within each collection while the
generated ordering snapshot preserves existing cross-collection behavior.

From `/opt/dataark`, using its Python environment:

```sh
# Preview a lossless split of the current combined manifest.
venv/bin/python tools/configuration_project.py split

# Write/refresh the project, refusing to overwrite manual edits.
venv/bin/python tools/configuration_project.py split --write

# Check that the project and combined manifest are exactly equivalent.
venv/bin/python tools/configuration_project.py check

# After editing files, compile a separate public snapshot for review.
venv/bin/python tools/configuration_project.py compile --output /tmp/ark-review.yaml

# After review, explicit local-root publication through the existing worker.
sudo venv/bin/python tools/configuration_project.py publish --write
```

The last command queues publication, it does not bypass validation or overwrite
private settings. It pins a fingerprint of the reviewed modular files and rejects
later edits. It also rejects a draft whose synchronization base predates a change
to the active manifest; reconcile that draft before publication rather than losing
newer updater changes. Local root is an administrative authorization boundary, independent
of the web caretaker password. The web API cannot supply this local override.

Do not hand-edit files while publication is running. If manual edits exist on
disk, the web editor warns and refuses unrelated publication until those edits are
compiled/reviewed/published. It shows the active compiled configuration, which may
differ from unpublished local drafts. Ordinary updater tools can still update the
combined manifest; refresh a clean project with `split --write` to reflect those
updates. Manual drafts are never silently overwritten; unchanged files keep their comments.

## Compatibility and recovery

This is an incremental migration. `dataark.yaml` remains the runtime compatibility
boundary for existing installers/updaters; they have not all been rewritten to
edit modular authoring files directly. The manifest loader and renderer also accept
`config/library/ark.yaml`, with artwork/cache paths still rooted at `/opt/dataark`.
Both formats must assemble to the same definitions and render the same dashboard.

`config/content/content.yaml` remains the restoration selection/recipe. The portable
configuration mirror includes a modular snapshot built from that recipe's saved
public manifest, plus the original combined snapshot and existing version/lock
information. It never regenerates desired selections from an empty drive. The
generated snapshot cache is `config/content/project-snapshot`; do not edit it as
the authoring project. The source checkpoint includes the authoring project and
compiler code. The two snapshots can represent different checkpoint times until
a new approved content profile is deliberately recorded.

Changing source/schema files changes a restoration plan's fingerprint. Re-plan and
approve the exact new plan before resuming recovery after such a change. Keep this
work on `feature/readme-foundation`; merge and dependable-recovery claims remain
deferred until spare-media acceptance passes.
