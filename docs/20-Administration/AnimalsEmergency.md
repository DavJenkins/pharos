# Pets and livestock during emergencies

The landing-page Pets & Livestock card opens `/library-files/family-resources/index.html#animals-emergency`. Seven unchanged PDFs (50 pages) cover animal preparedness and care continuity.

## Installed references

- AVMA Save the Whole Family pet-preparedness brochure: 7 pages in English and 7 in Spanish, November 2023 publisher files. Evacuation, supplies, food/water, records, shelter and sanitation.
- NYC My Pet’s Emergency Plan: 16 pages. Blank workbook for pet identification, transport, supplies and emergency arrangements; city services and shelter rules retain NYC scope.
- Iowa State CFSPH Disaster and Emergency Planning for Small Farms and Ranches (The Basics): 1 page, June 2023 publisher file. Shelter-in-place and evacuation preparation, animal inventory, feed/water, maps and contacts.
- USU Backyard Poultry Biosecurity: 6 pages, May 2017, AG/Poultry/2017-01pr. Historical disease references and original notices retained.
- UMN Operations Contingency Plan for Beef Producers: 6 pages, blank essential-care form.
- UMN Operations Contingency Plan for Dairy Producers: 7 pages, blank essential-care form.

UMN forms were obtained from public Google Drive files linked by the publisher's cattle-biosecurity page, reviewed in 2026. That page review date is not asserted to be the form revision date. These forms cover essential care when the usual caretaker is unavailable, not comprehensive veterinary management.

## Audit and scope

The old CDC pet-checklist recipe was unavailable; no installed pet/livestock collection was found. Its unavailable status is preserved. An AVMA e-business link returned a different 28-page 2015 disaster-preparedness publication; this was replaced before registration with the correct English 2023 pet brochure. An archived Iowa State test-server plan returned 404 and was omitted; the installed 2023 farm basics sheet and UMN care forms provide that coverage.

These guides support planning, not individualized veterinary treatment or authorization to transport animals during disease restrictions. Obtain species-appropriate feeding and medication instructions from the caretaker/veterinarian. Regional evacuation, shelter and animal-movement requirements may differ. Keep completed care plans, ownership records and private contact information on the user's device; only blank originals are shared by the Ark.

## Configuration and recovery

Human-readable recipes live in `deploy/reference/family-catalogue.json`. PDFs are under `/mnt/storage/family-resources/animals-emergency/`; `/mnt/storage/family-resources/sources.json` records original source pages, editions, retrieval times, page counts, sizes and SHA-256 hashes. Publisher originals are unmodified.

Refresh is manual. From `/opt/dataark`, run `/usr/bin/python3 tools/install_family_resources.py --register`, then export intentional library changes with `venv/bin/python tools/content_profile.py export`. The family restore recipe checks registered assets under `animals-emergency` before treating the collection as complete. Public configuration and metadata are mirrored to SSD recovery configuration and GitHub; PDFs remain on the content drive.

## Validation

All seven PDFs passed header and pdfinfo checks. Local links, the landing card, artwork and rendered documentation are checked after publishing. Content-profile tests cover missing animal-care files and reuse of a complete collection. Interactive form export is not claimed to have been fully acceptance-tested.
