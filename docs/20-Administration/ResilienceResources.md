# Survival, power, laws and PDF forms

The Ark preserves useful knowledge and tools for adverse conditions. Reading and using these browser tools is open to everyone; changing the shared library follows the caretaker controls. No internet is needed to read installed files or run the calculators and PDF editor.

## Entry points

- [Wilderness and off-grid references](/library-files/resilience/index.html)
- [Laws, regulations and code coverage](/library-files/civic-reference/index.html)
- [U.S. Code title index](/library-files/civic-reference/us-code/index.html)
- [Off-grid power planner](/power.html)
- [Fill a PDF](/pdf-forms.html)
- [Blank forms](/library-files/forms/index.html)

Both reference collections are represented on the landing page and in Manage Library. Files are also served through the existing read-only HTTP, SMB and anonymous FTP library paths. Source records are stored in each collection's `sources.json`, including source URL, retrieval time, edition, hash, size and failures. Text-only snapshots explicitly retain internet links; linked pages, images, video and interactive publisher searches are not implicitly archived.

## Installed coverage, October 23, 2026

Ten survival/power files were verified: Maine IFW's *You Alone in the Maine Woods*, NPS Ten Essentials, USGS Map and Compass (2001), Olympic National Park water/sanitation guidance, DOE/NREL solar basics (2009), DOE Solar Power in Your Community (2022), DOE small-wind web guidance and 2021 PDF, OSHA portable-generator guidance, and PNNL-33984 *Introductory Guide to Generating, Using and Storing Energy* (April 2023). Older manuals retain their dates; they are not current installation standards. First aid and survival skills still need practice and appropriate training. Existing WikiMed and iFixit collections complement these documents.

Sixty-seven civic files were verified:

- Official OLRC U.S. Code bulk release through Public Law 119-124, October 15, 2026: 58 title/appendix HTML files plus the unmodified source ZIP. This is a preliminary statutory snapshot, not all federal law. Uncodified laws, decisions, later amendments and most regulations are outside its coverage.
- U.S. Constitution, Senate document 111-4 (2010 pocket edition).
- FCC Part 97, Amateur Radio Service: complete October 1, 2025 annual PDF including emergency communications; not live eCFR.
- CFR Title 44 volume 1, 2025 annual edition. The official 2025 Title 44 bulk directory lists only volume 1; a mistakenly requested volume-2 target was removed on October 24. This is not all CFR titles or live eCFR.
- Massachusetts Constitution and selected General Laws: Chapter 186 (41/41 listed sections), Chapter 93A (11/11), Chapter 76 (31/31), including brief repeal notices. These are unofficial legislature website snapshots, not all Massachusetts law or court rules.
- Gardner's official City Code information page. The underlying ordinance text was not retrievable and is **not installed**.

Some U.S. Code titles are large (Title 42 is approximately 76 MiB). Use browser Find within a title, or download to a more capable device. Whole-code full-text search has not been implemented.

## Code and legal gaps

Massachusetts electrical, building and fire sources returned publisher access errors during installation. The catalogue keeps their official URLs and edition notes, without treating them as installed books. Source pages checked during research identified electrical amendments effective April 24, 2026 with the 2026 NFPA 70 base; the tenth building-code edition with concurrency ending June 30, 2025; and the 2021 state fire-code edition effective May 12, 2023. These notes are not substitutes for the code text or verification of subsequent changes. Proposed amendments must not be labeled adopted law.

Copyrighted ICC/NFPA base books have not been mirrored. An amendment does not contain the complete referenced model code. Massachusetts small-claims rules and Gardner ordinance text remain gaps. Legal currency, jurisdiction, applicability and later emergency orders must be checked; a retrieval timestamp is not an effective date.

Four survival/power source URLs also failed: two Forest Service PDFs, an older DOE microhydro page, and a Colorado hydro handbook. They are listed under unavailable sources. Those failed URLs remain historical records. On October 24 the publisher-hosted NCAT IP383 Micro-Hydro Power design/installation guide (February 2011, 28 pages) was installed as a dedicated alternative. Historical costs and permitting references are retained; it does not replace current codes or site-specific engineering. There are now eleven installed survival/power references.

## Power planner

The browser computes daily load energy as sum(watts × quantity × hours). Battery draw = load Wh / inverter efficiency + inverter idle watts × 24. Nominal battery Wh = daily draw × reserve days / usable fraction; Ah = Wh / nominal voltage. Solar array watts = daily draw / (peak-sun hours × system yield factor). All listed loads use the selected inverter efficiency; choose 100% for an all-DC estimate.

Microhydro watts = 9.81 × flow in L/s × net head in metres × overall efficiency. Daily energy assumes the usable flow continues for 24 hours. Example defaults are not measurements of this Ark or local solar conditions. These estimates do not size wiring, fuses, grounding, transfer equipment, startup surges or structural works. Print/save uses the browser's print dialog. Nothing is uploaded or saved to the Ark.

## PDF forms

Open a blank PDF already downloaded to your device. The browser reads up to 50 MB locally and supports AcroForm text, checkboxes, dropdowns, option lists and radio groups. Internal field names can be cryptic; preview the result. Required fields are labeled but incomplete drafts can be saved. Read-only fields stay read-only. Flat documents can receive placed text, checkmarks or a drawn signature mark. Preview before saving; added marks are page content. Optional flattening turns interactive fields into ordinary content; keep the blank original.

The locally bundled PDF.js renders pages, and pdf-lib with fontkit writes a new copy. DejaVu Sans supports many European languages, but not every script; unsupported characters cause a reported error. Encrypted PDFs, XFA, existing digital signatures, cryptographic signing and complex PDF portfolios are outside this tool's scope. A drawn mark is not a certificate-based digital signature. Work stays in tab memory until saved; do not close or reload with unsaved work. Completed private forms must not be placed in the public library.

The in-app browser successfully previewed text, accented characters, checkbox and dropdown values. Its generated-PDF download did not produce a retrievable download event during testing; a persistent “Save prepared PDF” link is provided. Verify saving in your normal browser before relying on this editor. Separate saved-file checks validated the PDF library's interactive field tree and flattening. Rotated-page mark placement, complex production forms and actual Android export remain unverified. PDF.js document loading-task cleanup was corrected in both this tool and the coloring tool.

## Installation, updates and restoration

Source repository: `/opt/dataark` on the Ark, [DavJenkins/pharos](https://github.com/DavJenkins/pharos) on GitHub. Content belongs on the mounted SSD, not in Git.

From `/opt/dataark`, using the installed Python environments:

```sh
sudo /usr/bin/python3 tools/install_pdf_forms.py
sudo /usr/bin/python3 tools/install_resilience.py --register
sudo bash deploy/deploy-web.sh
```

The reference installer requires PyYAML/app manifest dependencies, `pdfinfo` and `pdftotext`. It uses three bounded download workers and two workers for chapter sections. Individual source files are capped at 40 MiB; the U.S. Code ZIP at 250 MiB and expanded content at 1 GiB. Downloads validate PDF structure or substantive text before registration. Failures retain a previously verified copy when its hash still matches, and record the failed recheck. It does not bypass publisher access restrictions. Registration takes the updater lock and writes the two repository records and verified assets; it does not start another timer.

To reinstate removed reference files, rerun the installer. The retained source records and catalogue provide the URLs. This is a manual caretaker operation; these new collections have no automatic publisher-check interval. On an empty installation the installer discovers the official U.S. Code bulk archive. An existing source ZIP is hash-checked and reused: rerunning alone does **not** update its release. To move to a newer release, first preserve the old ZIP and metadata outside the public collection, then replace both with a verified official bulk release and matching URL, currency and SHA-256 in `us-code-source.json`, and rerun. Check source coverage and source records after each update.

`deploy/reference/resilience-catalogue.json` defines the non-Code sources. `tools/install_resilience.py` defines selected Massachusetts chapters, generates offline indexes and registers assets. `tools/install_pdf_forms.py` installs pinned official npm packages with SHA-512 checks; vendor provenance and original licensing files accompany them. The current checked-in vendor files permit ordinary web deployment without fetching packages. `tools/publish_content.py` refreshes the portable SSD catalogue. Avoid committing runtime `dataark.yaml`, private configuration, downloaded law archives or completed forms indiscriminately.

## Expansion list

Next useful categories: food preservation and gardening; water storage and sanitation; amateur/emergency radio and local communications; accessibility aids; practical mechanical repair and fabrication; expanded educational curricula at separate age levels. Obtain permitted offline copies with dates and attribution, verify viewers, register installed files on the landing page, and keep uninstalled possibilities in library management rather than prominent content cards.

## Amateur callsign database and grid proximity

[Offline callsign viewer](/callsigns.html) searches the FCC U.S. amateur license bulk release. Callsign-prefix, licensee-name word prefixes, state/territory, city-prefix and Maidenhead-grid filters can be combined. Active-only means the FCC snapshot status, not a current authorization guarantee. Other statuses remain searchable. Results are capped at 100 with a truncation notice. This is not an international callbook, GMRS dataset, application search, contact directory or live station tracker.

The FCC archive is retained as `civic-reference/fcc-amateur-source.zip`; the derived portable database is `callsigns.sqlite`. `callsigns-source.json` and the viewer show archive record dates, import time, counts, sources and hashes. The SQLite file contains the public licensee name, mailing city/state/ZIP, callsign, service, status and license dates; the original ZIP retains the complete FCC public release. Private phone/email fields are not indexed or displayed.

For proximity, the licensee's five-digit mailing ZIP is joined to the 2025 Census ZCTA representative point. ZCTAs approximate ZIP areas, not exact postal boundaries; some ZIPs have no match. A mailing ZIP does not identify a station or residence. Unmatched records are omitted from proximity searches. The input accepts 2, 4, 6 or 8 character Maidenhead locators, converts to the cell centre and calculates great-circle distance and initial bearing to the representative ZIP point. Bearings are degrees true, not magnetic. Coincident points have no meaningful bearing. Radius is 1–1000 km; the viewer also accepts miles. Broad grid cells and rural ZIP areas can produce substantial location error. No device GPS or internet geocoder is used.

Searches use the Ark-local read-only API `/api/callsigns/search`; the browser does not load the whole database into memory. SQLite indexes accelerate callsign, name and ZIP filters. Parameterized queries and bounded inputs/results prevent arbitrary SQL and unbounded responses. No public update endpoint is provided. The database is atomically replaced after an integrity check, so an interrupted rebuild preserves the previous published database.

Rebuild from retained sources, or explicitly refresh official files:

```sh
sudo /usr/bin/python3 /opt/dataark/tools/install_callsigns.py
sudo /usr/bin/python3 /opt/dataark/tools/install_callsigns.py --refresh
```

The installer takes the updater lock, bounds source sizes, validates ZIP checksums, streams FCC HD/EN records and builds SQLite FTS name search. Source download is approximately 189 MiB; allow additional working space for the old and new databases during replacement. Updates are manual; no new recurring scheduler is installed. The viewer is linked on the landing-page civic card and Other Ark Resources. After removal, a caretaker can rerun the installer to rebuild the database.

## Amateur-radio question drills

[Radio exam practice](/radio-study.html) contains 1,431 questions and 14 diagrams: Technician 2026–2030 (409), General 2023–2027 (423), Amateur Extra 2024–2028 (599). Validity dates and retrieval date appear in the tool. Outside those dates the tool warns that the pool is historical. This is unofficial practice, not exam administration or a grant of operating authority.

Questions are the NCVEC public-domain pools, obtained as a machine-readable transcription and diagram set from `russolsen/ham_radio_question_pool`, pinned to commit `6122699c9541f26d88298db379b5e252885c42a2`. Its Apache-2.0 license is retained. Files are not taken from a paid course. The four February 19, 2026 Technician wording corrections were checked exactly; all nine listed General withdrawals and four Extra withdrawals were checked absent against ARRL's October 23, 2026 list. Each question has four choices, a consistent numeric/letter key and a resolvable local figure. Pool counts and 35/35/50-group coverage are validated. Current compiled NCVEC PDF URLs returned access errors; the transcription provenance is disclosed rather than described as a downloaded official PDF. The answer keys and supplied rule references are included; there are no official teaching explanations.

Drill modes offer immediate feedback, topic filters, 10/25/all question rounds, and review of questions last answered incorrectly. Practice exams draw one question from each official group and defer correctness until the end; thresholds are 26/35 for Technician and General, 37/50 for Extra. Answers keep their published order. At completion the score and missed questions are shown. This is untimed practice, not a prediction of an official result.

Progress is saved in local browser storage on the learner's device, keyed by pool edition. It is not uploaded to the Ark. People sharing a browser share that progress; browser data clearing removes it. If browser storage is unavailable, practice continues in memory with a notice. There is a pool-specific reset control with confirmation. Figures, pool text and JSON are available offline; source hashes and dates are in `/mnt/storage/radio-study/source.json`.

Install or reinstate using:

```sh
sudo /usr/bin/python3 /opt/dataark/tools/install_radio_study.py
sudo bash /opt/dataark/deploy/deploy-web.sh
```

The installer uses the updater lock and pinned source files, validates the complete set before writing, registers the pools on the landing page and in Manage Library, and refreshes the portable catalogue. Updates are manual. To introduce a new pool or errata, review primary NCVEC/ARRL sources, update the pinned commit, expected counts, withdrawals, figures and dates, then revalidate the tool; rerunning the pinned installer alone does not promise new questions.

## Browser-captured state references

The Massachusetts electrical and fire amendment PDFs were subsequently captured successfully through the paired Chrome helper after automated requests failed. Their original edition notes and source hashes remain in civic-reference/sources.json. This does not supply the full copyrighted base codes, resolve every state-code gap, or establish later legal currency.
