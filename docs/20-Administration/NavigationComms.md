# Navigation and emergency communications

Two landing-page collections supplement local maps, radio tools and existing incident forms:

- `/library-files/family-resources/index.html#navigation-field`: four PDFs, 224 pages.
- `/library-files/family-resources/index.html#emergency-comms`: five PDFs, 132 pages.

## Navigation and field skills

USGS Topographic Map Symbols (4 pages) complements the existing Finding Your Way with Map and Compass reference under resilience. It describes historical topographic symbols; newer US Topo PDFs include their own symbol sheets. NWCG Basic Land Navigation, PMS 475, May 2016 (172 pages), covers map reading, compass bearings, declination, coordinates, GPS and navigation exercises. The file is preserved by GovInfo. NPS Trip Planning Guide Package, December 2022 (12 pages), includes trip preparation, trusted-contact planning and outdoor emergencies, including being lost or injured and signaling. It is not a technical search-and-rescue training manual. The existing CERT participant manual covers light search and rescue; this collection does not imply qualification for hazardous rescue operations.

FGDC / Delta State Reading and Understanding the US National Grid (36 pages) is an archived 2008-program slide deck. It includes coordinates, datum, UTM/USNG and GPS examples. Historic software and accuracy examples remain; some exercises refer to companion maps not installed here. USNG is not the amateur-radio Maidenhead locator system. Match datum, coordinate format and precision when sharing locations. Magnetic declination changes with time and place; old examples are not current declination for Massachusetts.

## Emergency communications and coordination

- ARRL fillable radiogram: 1 page, blank message form.
- ARRL message format, version 1.04, May 2002: 23 pages. Historical procedural reference; handling instructions and local practices may have changed.
- ARES Manual, March 2015: 94 pages. Archived organization and volunteer coordination guidance.
- DHS / SAFECOM Plain Language guide, hosted by CISA: 12 pages. Public-safety interoperability context, not permission to transmit on agency systems.
- Ready.gov Family Communication Plan for Kids, March 2020 publisher file: 2 pages. Blank contact and meeting-place cards.

The already-installed FEMA ICS booklet supplies ICS 205/205A communications planning, ICS 213 messages and ICS 214 activity logs. The failed CDC family-plan record remains accurately marked unavailable; the installed Ready.gov card now provides a local family-contact template without pretending that the CDC file downloaded. Current FCC Part 97, callbook and radio-study resources remain separate. Archived ARRL manuals are not substitutes for current regulations or serving-agency procedures.

Before an outage, agree on check-in times, primary and backup methods, an out-of-area contact and meeting places. Use the existing blank plans and logs to record that agreement. Keep completed plans with private contact information on the user's own device; the shared library stores only blank originals. No external messages or radio transmissions were sent.

## Configuration, refresh and recovery

Human-readable recipes are in `deploy/reference/family-catalogue.json`. PDFs are under `/mnt/storage/family-resources/navigation-field/` and `/mnt/storage/family-resources/emergency-comms/`. Metadata, editions, source pages, retrieval times, sizes and SHA-256 hashes are in `/mnt/storage/family-resources/sources.json`. Originals are not rewritten.

Refresh is manual: from `/opt/dataark`, run `/usr/bin/python3 tools/install_family_resources.py --register`, then export intentional library changes with `venv/bin/python tools/content_profile.py export`. Family restore checks assets in both repositories before treating an existing collection as complete. Public configuration and metadata are mirrored to SSD recovery configuration and GitHub; the PDF payload remains on the content drive.

## Validation

All nine PDF originals passed header and pdfinfo checks. Local PDF links, both landing cards, icons, supporting map and reference links, and rendered documentation are checked after publication. Focused content-profile tests cover missing assets in both collections and complete-collection reuse.
