# Paper, play and family resources

Added October 23, 2026. The Ark should support ordinary household life, learning and play as well as emergency repair and reference. These resources work over its local network without an upstream connection. Public reading and browser activities need no account; installation/removal remains a shared-library management operation.

## Find and use

The landing-page card Paper, Play & Family Resources links to Paper studio (/printables.html), games (/activities.html) and the local books index (/library-files/family-resources/index.html). PDF coloring is /coloring.html. The books index filters title/purpose, language and collection; audience guidance appears on every record. Printer needs are described in each activity rather than inferred from the presence of a PDF. Original third-party files and generated packs live on the SSD, so HTTP, read-only SMB and anonymous FTP can serve them through the existing content access methods.

Paper studio offers 28 patterns: square, engineering, dots, crosses, triangular/isometric grids and dots, hexagons, polar, log and semi-log, ruled/wide/narrow, handwriting/double-line/calligraphy, Cornell lines/grid/dots, music and guitar/bass tablature, character-writing squares, chess/checkers and Go boards, undated calendars, story/drawing and blank pages. Letter/A4, portrait/landscape, spacing, margin, color and line weight are adjustable where applicable. Board dimensions and staff groupings are fixed by the pattern. Browser printing saves PDF; SVG download preserves vectors. Print measured paper at actual size/100%, disable browser headers/footers, and check a ruler. Printer margins can limit edge coverage.

The ready-made Letter and A4 paper packs each have 28 pages. Each household pack has 14 blank record sheets: contacts, inventory, supplies, medication records, evacuation planning, pets, expenses, payment receipts, maintenance, equipment handovers, projects, community messages, volunteers and care notes. They are record aids, not official filings, treatment directions or universal contracts. Only blank files belong on public shares.

Games are memory pairs, two-person tic-tac-toe, a solvable sliding puzzle, and nature word hunt. The activity page also includes no-equipment story games, scavenger hunts, drawing prompts, paper folding and dots-and-boxes instructions. Games reset on leaving the page; there is no shared score store or account.

## PDF coloring

Mozilla PDF.js renders the chosen PDF locally on the user's device. Select a permitted library book or a local file (100 MB maximum), move between pages, then use brush, enclosed-area fill or paint eraser. Original PDF files are untouched. Page paint is retained only in the browser tab's memory; eight undo checkpoints are kept for the current page and discarded when switching pages. Save individual colored pages as PNG or print/save the current composed page through the browser. This is not a PDF annotation editor or a multi-page PDF exporter. Leaving/reloading loses unsaved work. Touch, pen and mouse use the same drawing surface; the canvas is not a keyboard-accessible painting interface.

Rendered pages are capped at roughly 1200 by 1600 pixels; large books and intricate fills still use the client's memory/CPU. Password-protected PDFs are not supported. Closed black outlines fill best. Imported PDF JavaScript evaluation is disabled, and the tool does not render external links or submit forms. It makes local same-origin requests for books, the worker, fonts, CMaps and WASM; there is no CDN dependency and no upload endpoint.

## Publishers and editions

The curated catalogue is deploy/reference/family-catalogue.json. NASA activity/coloring books, NPS Cave Scientist booklets, CDC coping/contact/planning materials, FEMA's archived September 2010 ICS booklet, and Common Paper agreements retain publisher format, attribution and edition. NPS Cave Scientist explicitly restricts reformatting/sale; those files are available unmodified for non-commercial educational use and excluded from the coloring tool's built-in list. CDC archive editions are labeled. Follow organization-required current incident forms rather than assuming an archived reference edition is the latest filing format. Contract templates require appropriate business and jurisdiction choices; the SOW accompanies the existing Common Paper PSA.

CDC publisher file downloads currently return HTTP 403 from this network, including its own archive. The five CDC candidates remain explicitly not installed; they are not advertised as local coping books.

The book index links publisher pages and keeps sources.json with resolved URLs, retrieval time, size, PDF page count, title excerpt, SHA-256 and rights notes. Failed publisher downloads are shown as not installed; an earlier local copy is retained only if it matches its recorded checksum. A retrieval date is not a new publication date. No publisher endorsement is implied.

## Installation, reinstatement and updates

Installers are explicit/manual; there is no new timer or background service. Run /usr/bin/python3 tools/install_family_resources.py --register on the Ark, then bash deploy/deploy-web.sh. This redownloads the supported catalogue and regenerates all four packs, including files previously removed through Manage library. It also reinstates their asset records. It needs the SSD mounted and the updater worker lock available; do not run alongside an active update or removal. Normal authorized system maintenance access is required. The catalogue is not a general-purpose user URL downloader.

The system Python uses Debian python3-reportlab plus existing PyYAML/Pillow and Poppler (pdfinfo/pdftotext). Generate just the four packs offline using /usr/bin/python3 tools/build_print_packs.py. Browser tools are static HTML/CSS/JavaScript: no Node build, database or additional network port. The PDF rendering dependency is pinned to PDF.js 6.4.299; tools/install_pdfjs.py downloads its official pdfjs-dist archive, checks the fixed SHA-512 integrity and copies only the required runtime, fonts, CMaps, WASM and license to app/static/assets/vendor/pdfjs. Its source.json records provenance. Vendored assets work without running the installer again. Check upstream security fixes during normal maintenance and deliberately update the pin/checksum together.

The registration lives in runtime dataark.yaml; maintain it through the installer rather than committing local content/device paths. The publisher files are content on the SSD, not Git blobs. Original tool code, catalogue, PDF builder, docs and PDF.js runtime are in /opt/dataark and the GitHub repository. Back up the SSD content and configuration separately; Git is not the full content backup.

## Verification record

October 23, 2026: all 174 existing Python tests passed; 252 generated SVG parameter combinations produced finite geometry. All 84 pages of the four generated PDF packs were rendered and visually reviewed. Browser checks covered custom paper selection, a local NASA PDF rendered by PDF.js, page navigation, paint, undo and PNG export, tic-tac-toe win detection, a legal sliding-puzzle move, word-hunt recognition and memory-card selection. Physical printing, Android touch behavior and a fully disconnected upstream session are not separately acceptance-tested. No new internet dependencies are required to run the static tools.

The in-app browser did not confirm the SVG download event during verification, although the generated vector and direct Blob download link were present without script errors. Use browser Print / Save PDF or the ready-made packs as the verified document path; native SVG download behavior should be checked in the target browser.

## Learning at home

/learning.html organizes existing local resources for early learners, elementary school, middle/high school and adult practical learning. It links Gutenberg, Wikipedia, iFixit, activities and paper tools. It does not add or claim a complete curriculum, teacher guides or assessments. Reader links use the current Ark hostname and Kiwix port 8080. A previously observed Kiwix article timeout is not resolved by this hub; the reader catalogue and actual article opening are separate checks.

## Adult coloring

The Adult coloring section contains Swarthmore’s 2021 North American Wild Flowers book (28 pages), JMU’s 2020 vintage illustrations (13 pages), and Europeana’s 2022 art collection (20 pages). They are available in the library book picker at `/coloring.html`, as original PDFs in `family-resources/adult-coloring/`, and in the family resources index. Page counts include covers and credits. Preserve each original page’s artist, institution, and license when sharing colored versions. Source URLs and use notes live in `deploy/reference/family-catalogue.json`; installed hashes and page counts live on the content drive in `family-resources/sources.json`.

## Holiday coloring

Two original CC0 packs are available under Holiday coloring in `/coloring.html`: Family Pages and Detailed Designs, each 14 pages. Themes include New Year, Lunar New Year, Valentine’s Day, St. Patrick’s Day, Easter, Earth Day, Independence Day, Halloween, Thanksgiving, Christmas, Hanukkah, Kwanzaa, Diwali and Eid. Suggested audiences describe drawing detail rather than formal age ratings.

The PDFs live in `/mnt/storage/family-resources/holidays/`. Rebuild with `/usr/bin/python3 /opt/dataark/tools/build_holiday_coloring.py`. The readable theme list is `deploy/reference/holiday-themes.json`; all vector artwork is generated from source. The family installer rebuilds and registers both packs during content restoration, and populated drive replication includes them. Source metadata, page counts and hashes are recorded in `family-resources/holidays/sources.json` and merged into the main family catalogue. They may be freely copied, colored, adapted and shared under CC0 1.0.

## Cookbooks and pantry meals

The family index has a Cooking & pantry meals section, linked directly from the landing-page family card. Installed originals are the EFNEP Preparedness & Resiliency guide (48 pages), USDA A Harvest of Recipes with USDA Foods (2013, 98 pages), and USDA Recipes and Tips for Healthy, Thrifty Meals (May 2000, 78 pages). They cover everyday meals, pantry staples, substitutions, kitchen basics and meal planning. Historical prices and nutrition-policy statements remain identified by edition. Original documents and notices are kept unchanged.

Files live in `family-resources/cookbooks/`, with source URLs in `deploy/reference/family-catalogue.json` and verified metadata in `family-resources/sources.json`. The family restoration recipe and populated drive replication include them. Good and Cheap was also considered, but its university mirror blocked retrieval and the author’s old direct download no longer returns a PDF; it is recorded as not installed, not presented as local content.

## Sanitation and hygiene

The sanitation catalogue is served through its own landing-page card and the family index’s Sanitation & hygiene section. It contains twelve original guides, posters, plans and printable labels (47 pages). See [Sanitation and hygiene](Sanitation.md) for exact editions, source-mirror details, regional limitations and restoration behavior.

## Drinking water

The dedicated [Drinking water collection](DrinkingWater.md) adds sources, storage, rainwater harvesting, treatment selection and testing. Its six original PDFs are also browsable from the family index.

## Shelter and winter readiness

The [shelter and winter collection](ShelterWinter.md) adds seven original references for winter outages, heating and generator safety, weatherization and frozen pipes.

## First aid and caregiving

The [first-aid and caregiving collection](FirstAidCare.md) adds original first-aid references, medication records and caregiver planning workbooks, including children, older adults and disability/access needs.

## Growing food and repairs

[Gardening and practical repairs](GardeningRepairs.md) documents the New England gardening collection and the short maintenance references that supplement local iFixit.

## Navigation and emergency communications

[Navigation and communication references](NavigationComms.md) document map and coordinate training, outdoor trip planning, radiograms, plain-language procedures and family contact cards.

## Pets and livestock

[Animal preparedness](AnimalsEmergency.md) documents evacuation, shelter, supplies, sanitation, poultry biosecurity and backup livestock-care forms.

## Disaster recovery

[Recovery and cleanup](DisasterRecovery.md) documents flood cleanout, cleanup hazards, contractor fraud and loss records, complementing the existing mold and CERT references.

## Disability preparedness

[Disability preparedness and MS temperature sensitivity](DisabilityPreparedness.md) adds original planning, medical-device power and temperature-sensitivity guides, linked to existing caregiver and medicine resources.
