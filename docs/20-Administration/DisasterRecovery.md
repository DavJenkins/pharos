# Disaster recovery and cleanup

The landing-page card opens `/library-files/family-resources/index.html#disaster-recovery`. Five original PDFs (71 PDF pages) supplement the existing mold-cleanup guides, first aid, generator/electrical safety and CERT participant manual.

## Installed coverage

- EPA Flood Cleanup and the Air in Your Home, revised August 2017: 15 landscape PDF sheets representing the 28-page booklet layout. Print landscape.
- Creating a Healthy Home: Field Guide for Cleanup of Flooded Homes, National Center for Healthy Housing and partners, hosted by HUD: 22 pages. Archived post-Katrina regional field guide covering cleanout, electrical and environmental hazards, debris, drying and planning.
- OSHA Keeping Workers Safe During Disaster Cleanup and Recovery, FS-3698, November 2013: 2 pages. Historical worker-safety guidance, not a complete current code.
- HUD Housing Counseling Disaster Recovery Toolkit: Avoiding Post-Disaster Scams and Fraud: 4 pages, original archived publisher edition.
- NAIC Post-Disaster Claims Guide, Maine Bureau of Insurance edition: 28 pages. Damage inventory, receipts, claims and recovery records. Maine contacts and state-specific legal context remain and are labeled.

The FTC handout URL returned 404 and the Massachusetts DOI disaster brochure returned 403; neither is represented as installed. HUD supplies the fraud guidance and the Maine-hosted NAIC guide supplies claims documentation. Existing mold originals are linked rather than duplicated. The CERT manual remains the broader preparedness and utility-safety reference.

## Scope

Reentry depends on official safety clearance; none of these books is a structural assessment or permission to handle damaged energized equipment or gas systems. Qualified utilities and professionals may be needed. Archived guidance preserves historical procedures and references; local disposal requirements, current safety rules and insurance policy terms take precedence. The claims guide is not a promise of coverage or a Massachusetts legal guide. Only blank/reference material is shared; completed inventories, insurance details and personal loss records belong on the user's own device.

## Configuration and recovery

Recipes are in `deploy/reference/family-catalogue.json`. Files live under `/mnt/storage/family-resources/disaster-recovery/`; source URLs, editions, retrieval times, page counts, sizes and SHA-256 hashes are in `/mnt/storage/family-resources/sources.json`. Originals remain unmodified.

Refresh is manual: run `/usr/bin/python3 tools/install_family_resources.py --register` from `/opt/dataark`, then export intentional changes with `venv/bin/python tools/content_profile.py export`. The family restore recipe checks the disaster-recovery repository before reusing a complete collection. Public recipes and metadata are mirrored to the SSD recovery kit and GitHub; PDFs remain on the content drive.

## Verification

Every PDF passed header and pdfinfo checks. All five local PDF links, the landing card, artwork, supporting preparedness link and rendered documentation are checked after publishing. Content-profile tests cover missing recovery files and complete-collection reuse.
