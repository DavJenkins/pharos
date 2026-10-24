# Shelter, heating and winter readiness

The landing-page card opens `/library-files/family-resources/index.html#shelter-winter`. Seven original PDFs (85 pages) supplement the existing MEMA Winter Weather Preparedness Toolkit and OSHA portable-generator guide.

## Installed material

- NWS winter preparedness checklist: 1 page.
- USFA Heating Your Home Safely: 1 page.
- CPSC Portable Generator Hazards, publication 5123, October 2021: 1 page.
- DOE Energy Saver, 2022: 56 pages, including air sealing, windows, insulation and heating efficiency. Historical prices and incentives retained.
- Texas A&M AgriLife Preventing and Thawing Frozen Pipes: 2 pages, archived handout hosted in 2016; southern-climate framing retained.
- NWS Winter Storms: The Deceptive Killers, 2008: 12 pages, including sheltering at home or in a vehicle and cold exposure. Historical alert terminology and contacts retained.
- FEMA How to Prepare for a Winter Storm, 2014 GovInfo archive: 12 pages.

FEMA newer direct PDFs returned HTTP 403 from the Ark; the installed FEMA item is explicitly the archived edition. A library mirror of a Red Cross page did not return a PDF and was replaced by the publisher-hosted Texas A&M handout. No failed item is represented as installed.

## Scope

This is household outage and winter preparedness, not a structural inspection or a comprehensive temporary-shelter construction course. DOE weatherization is preparation, not advice to seal combustion ventilation or block exits. Original safety procedures and appliance limitations remain intact. The CPSC generator sheet supplements the existing OSHA guide. No outdoor combustion equipment should be used to heat enclosed shelters.

## Configuration and restoration

Human-readable download recipes are in `deploy/reference/family-catalogue.json`. Installed metadata, editions, original source pages, PDF page counts, sizes and SHA-256 hashes are in `/mnt/storage/family-resources/sources.json`. PDFs live in `/mnt/storage/family-resources/shelter-winter/`. The family installer creates the index and registers assets under the `shelter-winter` repository.

Refresh explicitly with `/usr/bin/python3 tools/install_family_resources.py --register` from `/opt/dataark`; updates are manual. Export intentional changes using `venv/bin/python tools/content_profile.py export`. The family restore recipe checks all registered shelter-winter assets before skipping a complete existing collection. Configuration and public source snapshots are included in the SSD recovery copy and GitHub; PDFs remain on the content drive.

## Verification

All seven originals passed PDF header and pdfinfo checks. Local HTTP links, landing card, artwork and rendered documentation are checked after publishing. Content-profile tests exercise a missing shelter-winter guide as well as complete-collection reuse.
