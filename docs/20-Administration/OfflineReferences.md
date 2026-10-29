# Offline maps and preparedness references

## Purpose
The landing page presents installed, usable content. Online discovery links belong inside the collection or its maintenance documentation, not in prominent empty library cards.

## All 50 U.S. states street map
Open `/maps.html`. Map data, scripts, styles, glyphs and sprites are all local. The viewer initially shows the lower 48; Lower 48 / Alaska / Hawaii buttons reposition the view. Alaska includes the Aleutians and Hawaii includes the Northwestern Hawaiian Islands. Rectangular cutouts include neighboring areas; U.S. territories are not a promised coverage set. WebGL is required. Pan, zoom and scale are available; search and route planning are not implemented.

The active archive is `/mnt/storage/maps/osm/usa.pmtiles`, exposed at `/library-files/maps/osm/usa.pmtiles`. Native zooms are 0–15; higher viewer zooms enlarge existing detail. Source: Protomaps build 22 October 2026. Coverage geometry and source/checksum are in `deploy/reference/osm-usa.geojson`, `osm-usa.json`, and the drive's `maps/osm/source.json`. The earlier Massachusetts file and `massachusetts-source.json` remain for rollback; the old download link refers to that older regional copy. Existing flood, parcel and topographic datasets remain Massachusetts-focused and separate.

Attribution: OpenStreetMap contributors (ODbL), Protomaps Produced Work and Natural Earth. Preserve attribution when copying. See https://www.openstreetmap.org/copyright and https://docs.protomaps.com/basemaps/downloads . Software and font license notices are retained with the local viewer dependencies.

### Reconstruction and updates
The street basemap remains manually updated, independent of monthly GIS and Kiwix workers. `tools/content_profile.py restore --only osm --apply` reconstructs the selected national archive from the public source recipe, verifies it, checks the recorded hash and publishes atomically. The regional source cutout is downloaded, not the entire planet. The content profile and its geometry travel in DATA-ARK-CONFIG and the recovery kit. Source availability is required. For a different build, review the source edition, checksum and viewer date together.

## Preparedness and CERT
Local contents and provenance: `/library-files/preparedness/index.html` and `sources.json`. Installed: FEMA / Ready.gov Are You Ready? (2021 hosted edition), CERT Basic Training Participant Manual (2019), and CERT Hazard Annexes (2019). Files are unmodified PDFs with source URLs, retrieval dates, sizes and SHA-256 hashes. They are reference editions, not a claim of current certification or a replacement for practical training.

Massachusetts MEMA's English preparedness flyer and Winter Weather Preparedness Toolkit 2026 were identified but the publisher returned HTTP 403 to downloads. The CERT all-abilities annex was likewise blocked. They are explicitly pending, not installed. Existing FEMA flood GIS data is unrelated to these manuals.

USA.gov is useful as a directory for disaster assistance, benefits, housing and official contacts. Preserve durable underlying agency guides. A stale mirror cannot provide live alerts, applications or current eligibility decisions. Online reference: https://www.usa.gov/disasters-and-emergencies . Massachusetts source list: https://www.mass.gov/lists/emergency-preparedness-flyers-and-toolkits .

`tools/install_offline_references.py` explicitly fetches pinned viewer dependencies and the curated PDF list, validates package integrity and PDF signatures, and records document hashes. It does not register content or deploy the site. Rerunning may refresh official PDFs; review records and update manifest hashes afterward. It has no schedule and must be run deliberately with caretaker filesystem privileges. These new assets use manual update policy. Their normal library removal controls require caretaker authorization; the generic library Reinstate button does not cover every reference type. The content restoration profile has separate national/Caribbean PMTiles recipes and reference installers; use the appropriate recorded recipe, then verify registration and viewer availability.

## National map reconstruction and validation

The installed national archive is 20,984,940,063 bytes (about 19.54 GiB), covering the lower 48, Alaska/Aleutians and Hawaii/Northwestern Hawaiian Islands. `deploy/reference/osm-usa.geojson` defines coverage and `osm-usa.json` pins the source. `tools/extract_usa_map.py` stages and verifies a replacement; a separate publisher activates it. The extraction unit applies a 1000 MiB memory ceiling and lower CPU/I/O priority, retaining the working map on failure. Territories outside the national coverage are not implied; the Caribbean is a separate collection.

Extraction requires the kernel memory controller. Check `memory` in `/sys/fs/cgroup/cgroup.controllers` before running the extraction unit. If absent, `deploy/enable_memory_limits.py --apply` can prepare the reviewed boot flag and backup; it does not reboot. Verify after reboot. Do not assume a unit file alone establishes effective resource limits.

Published national map SHA-256: `e725aa7f1fdf0bac4893d5d36aa479ea682a0b9e87f1c9f0cbe0ebf84350f663`; 20984940063 bytes. Verified before replacing the active viewer target.

## Caribbean islands street map

Open `/maps.html?collection=caribbean`. This is a separate offline archive, not a replacement for the U.S. collection. Shortcuts frame Sint Maarten/Saint-Martin, USVI/BVI, Puerto Rico and the Bahamas. The source cutout spans longitude -89 to -58 and latitude 9 to 28, including the Greater and Lesser Antilles, Bahamas/Turks and Caicos, Cayman Islands, the ABC islands, Trinidad and Tobago, and adjoining mainland/coastal areas. Bermuda is outside this coverage. The source is the same pinned 22 October 2026 Protomaps build as the U.S. map, native zooms 0–15.

The archive is `/mnt/storage/maps/osm/caribbean.pmtiles`, exposed at `/library-files/maps/osm/caribbean.pmtiles`. Source, bounding box, verified size and checksum are recorded in `deploy/reference/osm-caribbean.json` and `maps/osm/caribbean-source.json`. Pan and zoom work offline using local scripts, styles, fonts and sprites. This is a street basemap, not a nautical chart, marine navigation aid, or route planner.

The public content profile includes recipe `osm-caribbean`. Restore missing content with `python3 tools/content_profile.py restore --only osm-caribbean --apply`. Configuration and the pinned source/checksum travel in DATA-ARK-CONFIG and the recovery materials. First installation uses `tools/install_caribbean_map.py` with the resumable loopback source helper; the active archive is published only after verification. Maintain OSM/Protomaps/Natural Earth attribution.
