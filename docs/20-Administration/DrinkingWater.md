# Drinking water

The landing-page Drinking Water card opens `/library-files/family-resources/index.html#drinking-water`. Six original PDFs (127 pages) are installed locally: EPA emergency disinfection (September 2017, 2 pages), EPA home testing (May 2005, 2), EPA household wells (24), EPA WaterSense treatment selection (November 2024, 9), Texas rainwater harvesting (third edition 2005, 88), and USU Extension water-storage tips (2). Original editions, contacts, institutional notices and regional scope remain intact.

## Coverage and limits

Storage and household sources complement existing FEMA food-and-water, FDA outage and NPS wilderness-treatment references. Rainwater catchment, first-flush systems, cistern sizing and treatment are covered by the Texas manual; its costs, rainfall and legal references are historical and regional. Well sampling and certified-laboratory testing are covered by EPA. Treatment selection is contaminant-specific; boiling or disinfection does not make chemically contaminated water safe. These originals are reference material, not a certification of a particular water source.

The CDC emergency PDF returned HTTP 403 from the Ark and is not represented as installed. EPA provides the installed emergency-disinfection reference. No online-only placeholder card was added.

## Configuration and restoration

Sources live in `deploy/reference/family-catalogue.json`; installed metadata, page counts, sizes and SHA-256 hashes live in `/mnt/storage/family-resources/sources.json`. Files are under `/mnt/storage/family-resources/drinking-water/`. The family installer downloads unchanged publisher files, validates PDF headers and page counts, retains verified copies on publisher failure, builds the index and registers assets in the `drinking-water` repository.

Run `/usr/bin/python3 tools/install_family_resources.py --register` from `/opt/dataark` for explicit refresh. Refresh is manual, not a scheduled promise of revised editions. Export intentional library changes with `venv/bin/python tools/content_profile.py export`. The family restoration recipe checks this repository along with family, food-preservation and sanitation assets before treating the collection as complete. Public configuration and source metadata are mirrored to the SSD recovery kit and saved in GitHub; large PDFs remain on the content drive.

## Verification

All six PDFs were parsed with pdfinfo and linked through the local HTTP server. Manifest and content-profile tests cover registration and missing-file restoration behavior.
