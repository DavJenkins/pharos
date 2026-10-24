# Disability preparedness and MS temperature sensitivity

The offline collection is at [Disability preparedness](/library-files/family-resources/index.html#disability-preparedness), linked from its own installed-content landing card. It supports people with disabilities and their chosen support network; no diagnosis, personal plan or completed health record is stored publicly.

## Installed originals

- **OHSU / Oregon Office on Disability and Health, Ready Now!**, second edition updated October 2023 (publisher file hosted May 2026): 148 PDF pages. Plain-language personal assessment, support group, communication, mobility, evacuation, service animals and planning forms. The publisher calls the collection 150 pages; this downloaded PDF has 148. Regional contacts are retained. OHSU reports digital accessibility improvements are still pending; plain language does not mean every PDF feature is screen-reader accessible. CC BY-NC-ND 3.0 US: preserve the original, attribution and noncommercial terms; no coloring derivatives.
- **FDA, Home Use Devices: How to Prepare for and Handle Power Outages for Medical Devices that Require Electricity**: 20 PDF pages. Archived 2011 booklet still linked on the FDA home-health page. Device-specific questions, batteries, contacts and checks after power returns. Some cover pages are image based.
- **MS Society UK, Hot and Cold: The Effects of Temperature on MS**, May 2016: 6 PDF pages. Archived temperature-sensitivity and cooling reference; UK contacts and historical recommendations are preserved. The current MS Society and MS Trust temperature pages were consulted to check scope, but are not represented as downloaded offline copies.
- **American Red Cross, Disaster Preparedness for People With Disabilities**: 48 PDF pages, archived edition hosted by Alaska emergency management. Personal support networks, mobility, evacuation, communication, supplies and service animals. Historical contacts and procedures are not assumed current.

Total: four original PDFs, 222 PDF pages. Copies remain unmodified. Original copyright and institutional notices are retained; no agency endorsement is implied. The three Australian Red Cross resources attempted during setup returned HTTP 403 and were omitted from installed recipes and metadata.

## How the collection fits

Use Ready Now! as the main planning workbook. Follow links to the existing first-aid/care collection for the FDA medication record, archived safe-drug-use guide, FEMA caregiver plan and English/Spanish NYC planning workbooks. Animal preparedness and shelter/winter collections provide related references without duplicate copies.

Plan around individual needs: temperature and fatigue, accessible transport, communication methods that work without internet, backup supporters, mobility aids, medication cold storage and equipment power runtime. Storage limits and backup power compatibility must come from the medicine labeling, pharmacist, care team or equipment manufacturer; the Ark does not prescribe treatment or device settings. Do not assume that a new or worsening symptom is caused by temperature alone. The MS reference is educational, not an individualized care plan.

Downloaded forms are blank public references. Save completed plans, medication lists, emergency contacts and insurance identifiers on the user's own device or paper, not the public library. Downloading a form does not assert that every PDF form field or export workflow has been tested.

## Recipes, restore and updates

- Original source URLs, edition, purpose and usage notices: `deploy/reference/family-catalogue.json`, collection `disability-preparedness`.
- Actual installed status, resolved URL, size, page count, retrieval time and SHA-256: `/mnt/storage/family-resources/sources.json`.
- Files: `/mnt/storage/family-resources/disability-preparedness/`.
- Installer/index/manifest registration: `tools/install_family_resources.py`; repository ID `disability-preparedness`.
- Original pictogram: `tools/build_collection_icons.py`, `app/static/assets/icons/Accessibility.png`.
- Exported selection and public snapshots: `config/content/`; mirrored in `/mnt/storage/DATA-ARK-CONFIG` and paired with the public source checkpoint in `/mnt/storage/DATA-ARK-RECOVERY`.

These references use manual updates (`refresh_interval: never`). Re-run the family installer deliberately to check publishers, then export the content profile and publish. The family restore completeness check includes this repository, so removing a new guide does not incorrectly reuse only the older family files. Payload PDFs are on the content drive, not in Git; recipes and hashes are in the repository. Source: `/opt/dataark` locally and [DavJenkins/pharos on GitHub](https://github.com/DavJenkins/pharos), branch `feature/readme-foundation`.

## Publisher references

- [OHSU toolkit and license](https://www.ohsu.edu/university-center-excellence-development-disability/ready-now-emergency-preparedness-tool-kit)
- [FDA home-health devices and outage booklet](https://www.fda.gov/medical-devices/products-and-medical-procedures/home-health-and-consumer-devices)
- [MS Society current temperature information](https://www.mssociety.org.uk/about-ms/signs-and-symptoms/effects-temperature-ms)
- [MS Trust current temperature information](https://mstrust.org.uk/a-z/temperature-sensitivity)
- [FDA current safe-drug-use information](https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster) (internet required; the existing local PDF is an October 2023 snapshot)

Validation: each new file was checked for a PDF header, parsed with pdfinfo, hashed and served by its local HTTP link. Focused profile tests cover restoration when any collection guide is missing. Index and landing card receive a live browser check after deployment.
