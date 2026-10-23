# Offline maps and preparedness references

## Purpose
The landing page presents installed, usable content. Online discovery links belong inside the collection or its maintenance documentation, not in prominent empty library cards.

## Massachusetts street map
Open `/maps.html` on the Ark. Its map data, JavaScript, styles, glyphs and sprites are all served locally. The viewer uses MapLibre GL 5.24.0, PMTiles JavaScript 4.5.0 and Protomaps basemaps 5.7.2. Browser WebGL support is required. Pan, zoom and scale are available; address search, directions and route planning are not implemented.

The regional PMTiles archive is `/mnt/storage/maps/osm/massachusetts.pmtiles`, exposed at `/library-files/maps/osm/massachusetts.pmtiles`. It covers bounding box west -73.51, south 41.23, east -69.90, north 42.89: Massachusetts and adjoining border areas, not all New England. Native zooms are 0–15; higher viewer zooms enlarge existing detail. The source is the October 22, 2026 Protomaps build. Nearby content at the boundary can be incomplete. Existing flood, parcel and topographic resources remain separate.

OpenStreetMap contributors: https://www.openstreetmap.org/copyright . OpenStreetMap data is licensed under ODbL; Protomaps basemaps are a Produced Work. Preserve attribution when redistributing. Natural Earth data also contributes to the basemap. See https://docs.protomaps.com/basemaps/downloads . Font and software license notices accompany the vendored assets.

Source URL, coverage and extracted-file SHA-256 are in `/mnt/storage/maps/osm/source.json`. Browser dependencies and their integrity records are under `app/static/assets/vendor/maps/`; Protomaps assets are pinned to commit 028c18f713baecad011301ff7a69acc39bcc2ae7.

### Rebuilding
This map is currently **manual update**, not part of the monthly GIS map worker or the Kiwix updater. No bandwidth cap is configured for this explicit extraction. Do not replace it by downloading the source planet archive (about 139 GB).

Install the official ARM64 `pmtiles` CLI 1.31.2 at `/usr/local/bin/pmtiles`. Its release tarball SHA-256 is f8bd47e7ea866863489cad588fbaf2f31f42e5821f7a03f009b3769f05801cb1. Official release: https://github.com/protomaps/go-pmtiles/releases/tag/v1.31.2 . Extract into a new staging filename, verify, then atomically replace the published archive:

```sh
pmtiles extract https://build.protomaps.com/20261022.pmtiles /mnt/storage/maps/osm/massachusetts.new.pmtiles --bbox=-73.51,41.23,-69.90,42.89 --maxzoom=15 --download-threads=2
pmtiles verify /mnt/storage/maps/osm/massachusetts.new.pmtiles
mv /mnt/storage/maps/osm/massachusetts.new.pmtiles /mnt/storage/maps/osm/massachusetts.pmtiles
```

For a later release, inspect the official build index at https://maps.protomaps.com/builds/ and update the source record, registered title and viewer date together. Apache must support HTTP byte ranges; the viewer reads only the needed portions of the archive. The file can also be copied through the Ark's existing read-only content access methods.

## Preparedness and CERT
Local contents and provenance: `/library-files/preparedness/index.html` and `sources.json`. Installed: FEMA / Ready.gov Are You Ready? (2021 hosted edition), CERT Basic Training Participant Manual (2019), and CERT Hazard Annexes (2019). Files are unmodified PDFs with source URLs, retrieval dates, sizes and SHA-256 hashes. They are reference editions, not a claim of current certification or a replacement for practical training.

Massachusetts MEMA's English preparedness flyer and Winter Weather Preparedness Toolkit 2026 were identified but the publisher returned HTTP 403 to downloads. The CERT all-abilities annex was likewise blocked. They are explicitly pending, not installed. Existing FEMA flood GIS data is unrelated to these manuals.

USA.gov is useful as a directory for disaster assistance, benefits, housing and official contacts. Preserve durable underlying agency guides. A stale mirror cannot provide live alerts, applications or current eligibility decisions. Online reference: https://www.usa.gov/disasters-and-emergencies . Massachusetts source list: https://www.mass.gov/lists/emergency-preparedness-flyers-and-toolkits .

`tools/install_offline_references.py` explicitly fetches pinned viewer dependencies and the curated PDF list, validates package integrity and PDF signatures, and records document hashes. It does not register content or deploy the site. Rerunning may refresh official PDFs; review records and update manifest hashes afterward. It has no schedule and must be run deliberately with caretaker filesystem privileges. These new assets use manual update policy. Their normal library removal controls require caretaker authorization; the current generic restore workflow does not automatically re-extract a regional PMTiles archive or re-fetch these PDFs. Reinstatement currently uses the documented commands/tool, followed by manifest registration.
