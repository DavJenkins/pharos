# First aid and caregiving

The landing-page First Aid & Caregiving card opens `/library-files/family-resources/index.html#first-aid-care`. Nine unchanged PDFs (713 pages) supplement WikiMed and the CERT manual already installed.

## Installed coverage

- IFRC International First Aid, Resuscitation and Education Guidelines 2025, published March 2026: 594 pages. Comprehensive evidence and teaching reference for first aid, resuscitation, bleeding, burns, fractures, environmental injuries and mental distress; not a short emergency checklist. IFRC permits non-commercial copying with acknowledgement. Original photos, copyright and notices remain intact.
- ACS What Everyone Should Know to Stop Bleeding After an Injury, 2017: 16 pages. Original training booklet hosted by Indiana DHS. A shorter practical reference; not a substitute for skills training.
- FDA My Medicine Record, Form 3664, March 2011: 4 pages. Blank printable/fillable medication record, not prescribing advice.
- NIA Six Tips on How Older Adults Can Prepare for a Disaster: 2 pages.
- FEMA / Rosalynn Carter Institute Disaster Preparedness Guide for Caregivers, 2024 file: 21 pages. Care recipient needs, support networks and continuity planning.
- NYC My Emergency Plan, English and Spanish: 30 pages each. Disability and access needs, health information, support networks and evacuation. City-specific contacts and services are retained and labeled.
- FDA Safe Drug Use After a Natural Disaster, webpage archived October 16, 2023 by MESH Coalition: 3 pages. Storage, contamination and refrigeration considerations; not individualized dosing or insulin-substitution instructions.
- AAP The Road to Readiness: Preparing Your Family for Disasters: 13 pages. Family preparation, children with special healthcare needs, reunification and emotional support. The publisher page updated September 2024 links this file; that page date is not asserted to be the PDF revision date.

## Scope and privacy

These originals support first aid and preparation when professional help is delayed; they do not provide definitive care for every emergency or certify users. Seek emergency assistance when available and work within training. The comprehensive IFRC reference includes scientific and educator material; use its topic index rather than treating all 594 pages as quick instructions. Publisher emergency numbers retain their jurisdictional context.

Only blank forms are shared. Save completed medicine and emergency-plan records on the user's own device; do not upload private health records to the public library. The existing PDF tool may be used where supported, but no claim is made here that every form's interactive export has been acceptance-tested.

## Sources, updates and recovery

Recipes are in `deploy/reference/family-catalogue.json`; downloaded metadata, page counts, sizes and SHA-256 hashes are in `/mnt/storage/family-resources/sources.json`. PDFs are under `/mnt/storage/family-resources/first-aid-care/`. Source pages and edition notes appear in the local index. Original files are not rewritten.

The Mayo-hosted bleeding booklet returned HTTP 403; the installed copy is from Indiana DHS. The CDC June 2026 pregnancy/infant/child handout returned HTTP 403 and is not installed or shown as a local guide. The AAP toolkit supplies family and child planning coverage.

Updates are manual. From `/opt/dataark`, run `/usr/bin/python3 tools/install_family_resources.py --register` for explicit refresh, then export intentional selections with `venv/bin/python tools/content_profile.py export`. The family restore recipe includes the first-aid-care repository when deciding whether an existing collection is complete. Public recipes and metadata are mirrored to SSD recovery configuration and GitHub; the large PDFs stay on the content drive.

## Validation

Each original passed PDF-header and pdfinfo checks. Local HTTP PDF links, the landing card, artwork and rendered documentation are checked after deployment. Focused content-profile tests cover missing first-aid-care assets and complete-collection reuse.
