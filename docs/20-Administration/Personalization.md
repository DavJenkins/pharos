# Personalization and household content interests

The optional top-level `personalization` section in `/opt/dataark/dataark.yaml` records why particular content belongs on this Ark. Version 1 supports `languages`, `jurisdictions_of_interest`, `vehicles`, and `destinations`.

Each vehicle has a unique `id`, integer `year`, `make`, `model`, optional `body_style`, and `asset_ids` referring to registered manuals. Each destination has an `id`, `name`, optional `asset_ids` and optional Ark-relative `viewer_url`. References are checked when the manifest is loaded. Empty lists are valid; older manifests without personalization still work.

The initial profile records the 2017 Honda Accord and Civic four-door sedans, Sint Maarten / Saint Martin, the U.S. Virgin Islands and the Caribbean collection. English and US/Massachusetts are interests, not restrictions on the wider installed library. A destination entry does not claim that every possible resource for that place is installed.

These are human-readable content preferences. They do not silently download, remove, restrict, or filter content. The asset/source recipes remain the exact instructions for acquisition and rebuilding. Add a supported content asset and its source recipe before referencing its ID here; an interest without an installed asset may use an empty `asset_ids` list.

The content exporter includes personalization in `config/content/public-manifest.yaml`, the content-drive `DATA-ARK-CONFIG` mirror and recovery source. Restoration carries it back into the live manifest while preserving appliance system settings. Treat it as public, portable configuration: do not add VINs, registration numbers, credentials, home addresses or travel dates. Review or clear the section before sharing a personalized clone. A future preference editor can use this same schema; no separate settings UI is currently required.

After editing, validate/render the manifest and export the content profile. Do not export an empty drive over an existing profile. See [Content restoration](ContentRestoration.md).
