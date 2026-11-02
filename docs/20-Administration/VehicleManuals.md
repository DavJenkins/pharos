# Vehicle documents and source notices

Vehicle documents are selected by the source catalogue and linked to vehicles through personalization. The Vehicle Manuals card and [vehicle document index](/library-files/vehicles/index.html) identify the configured documents and their publisher, document type, scope, applicability and rights notices. Original PDFs are also available through the public file share and anonymous FTP.

A vehicle’s make, model and year do not establish the contents or licensing of a document. Owner manuals, quick guides and workshop/service manuals are different document types. Their scope and any applicability limits come from explicit source metadata. Match the document to the vehicle and its equipment before following a procedure.

## Human-readable source metadata

`deploy/reference/vehicle-manuals.json` contains `schema: 1`, collection-level `repository` settings, shared `defaults`, and a `documents` list. Each document declares:

- Its ID, title, HTTPS publisher URL, model year and model.
- Publisher and document type.
- Scope, applicability and publisher/rights notice. Defaults are explicit catalogue data and can be overridden per document.
- Optional additional `validation_text` fragments, pinned size and SHA-256.

Personalization’s `asset_ids` select these source records; they do not generate new claims about a publisher, license, trim, engine or document coverage. Adding another manufacturer or model requires catalogue data, not manufacturer-specific Python.

## Acquisition, provenance and restoration

The installer validates the configured year/model and any additional text against the PDF. It records file size, SHA-256 and retrieval time. Source statements are copied from the catalogue; they are not inferred from the PDF or vehicle name. Source notices are rendered from those records.

```bash
sudo /usr/bin/python3 /opt/dataark/tools/install_vehicle_manuals.py
```

To refresh notices against already verified files without downloading or rewriting PDFs:

```bash
sudo /usr/bin/python3 /opt/dataark/tools/install_vehicle_manuals.py --metadata-only
```

Verified files and provenance are stored in `/mnt/storage/vehicles/`. A metadata-only refresh preserves the original retrieval time and records its own metadata-update time. Missing files or checksum/identity mismatches fail without treating the document as newly acquired.

Configured publisher certificate-chain additions live in `deploy/reference/source-tls.json`. They apply only to the named host and retain standard system trust and hostname verification. Certificate paths must remain inside the reference directory. Certificate verification is never disabled.

The content recipe and configuration mirror preserve the source definitions and notices. Populated-drive replication copies the original public vehicle PDFs. Public availability or a catalogue entry does not grant additional rights; retain each publisher’s notices.
