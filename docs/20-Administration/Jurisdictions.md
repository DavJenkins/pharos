# State and territorial legal coverage

The Ark includes a compact constitutional-text baseline for all 50 states,
the District of Columbia, Puerto Rico and the Northern Mariana Islands.
American Samoa, Guam and the U.S. Virgin Islands currently link to the locally
stored federal Title 48 framework; that is not a local constitution or code.

Open `/library-files/civic-reference/jurisdictions/index.html` for exact coverage.
Documents are snapshots. Retrieval dates do not establish legal currency.
Entire state statute codes, regulations, case law, local ordinances, uncodified
laws and later amendments are not implied by a jurisdiction entry.

## Sources and regeneration

`deploy/reference/jurisdictions.json` is the human-readable source catalogue.
It records official state sources discovered via Cornell LII and an attributed
University of Wisconsin 50 Constitutions fallback referenced by the Library of
Congress. Only constitutional provision fields are extracted from the fallback;
research annotations and history are excluded. Retain attribution and original
notices; the university fallback is for noncommercial educational/reference use.

Run `/usr/bin/python3 tools/install_jurisdictions.py --acquire` from `/opt/dataark`.
The installer verifies PDF structure, substantial text, jurisdiction identity,
constitutional subject, and legislative/executive provisions. It refuses short
index pages, encrypted PDFs and obvious access-denied pages. TLS validation stays
on. Publisher snapshots may be dated; failures remain explicit gaps. It reuses
verified local files, so repair runs do not discard good copies.

Acquisition uses two workers, at most nine candidate pages per jurisdiction,
50 MiB per document and a 2 GiB registration cap. Actual first acquisition was
about 43 MiB. Source URLs, retrieval times, hashes, failed attempts, provenance
and counts of extracted provisions are in `sources.json` beside the content.

The content profile has a `jurisdictions` recipe after `resilience`. Its catalogue
and source snapshot travel in DATA-ARK-CONFIG; source and installer travel in
DATA-ARK-RECOVERY. Restoring from configuration requires internet and an available
publisher, as with other collections. Existing verified copies are reused.

## Geographic expansion policy

Compact constitutions and national reference text justify nationwide coverage.
Public state statute bulk downloads also merit nationwide acquisition where
publishers provide verified complete editions; do not substitute a website index
for a code. Record volume, edition and any incomplete chapters before activation.
Common blank forms and official preparedness guides are suitable for broad
coverage when editions and identity can be verified. Site-specific instructions,
forms requiring personal details and completed forms are not public collection
material. Keep detailed parcels, topographic PDFs and imagery regional; all-area
imagery and municipal archives have much higher storage/update costs. Commercial
model-code books require a lawful source/license and are not scraped from viewers.
