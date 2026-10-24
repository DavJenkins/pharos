# Growing food and practical repairs

Two landing-page collections supplement the installed iFixit archive and existing food-preservation guides:

- `/library-files/family-resources/index.html#growing-food`: six PDFs, 427 pages.
- `/library-files/family-resources/index.html#repairs`: eight PDFs, 71 pages.

## Growing food

UMass supplies a Massachusetts vegetable planting chart (1 page) and seed-saving guide (2). UMaine supplies How Compost Happens, Bulletin 1159, updated 2021 (4), and Vegetable Varieties for Maine Gardens, Bulletin 2190, January 2022 publisher file (2). The Northeast Vegetable and Strawberry Pest Identification Guide is a 2018 publisher file posted August 2024 (56). Regional timing must be adjusted to local frost, elevation and growing conditions. Pest photographs identify problems; they are not pesticide application authorization. Current labels and local requirements take precedence.

The UNH resource indexed by search as a planting chart actually contains 362 pages of gardening reference chapters, beginning with botany and covering soils, nutrition, propagation and vegetable growing. It includes the planting chart. It is labeled Gardening Reference Chapters, not misrepresented as a short chart. File metadata says assembled January 2017; chapter revision dates are unspecified and historical citations remain. No pages were removed or rewritten.

## Practical repairs

- OSHA Hand and Power Tools, publication 3080, revised 2002: 32 pages. Historical occupational safety reference, not a complete current code.
- CPSC Home Electrical Safety Checklist, publication 513: 11 pages. Inspection and hazard identification, not live-circuit repair instructions.
- EPA WaterSense maintenance checklist, March 2024: 1 page. Leak and plumbing checks, not a full plumbing-repair manual.
- Portland bicycle maintenance and flat-tire repair: 2 pages.
- Briggs & Stratton small-engine tune-up schedule: 1 page. Generic intervals; obtain the correct engine and equipment manual before servicing. This is not a model-specific engine repair manual.
- Karma Co-op Fabric Cafe: beginning hand sewing/buttons (10), hand stitches for seams (8), and repairing fabric holes (6). Original public handouts and institutional notices retained.

The installed December 2025 iFixit archive reports 103,480 articles. Its local household, apparel and tool categories were checked, including Clothing and Patagonia Clothing. Some individual outgoing references can still say not yet available; an archive is not proof that every manufacturer page was mirrored. The new repair section links to the existing local Kiwix reader at `http://dataark:8080/content/ifixit_en_all_2025-12`.

## Configuration, updates and restoration

Recipes live in `deploy/reference/family-catalogue.json`. Files are under `/mnt/storage/family-resources/growing-food/` and `/mnt/storage/family-resources/repairs/`. Page counts, original source URLs, retrieval times, file sizes and SHA-256 hashes are in `/mnt/storage/family-resources/sources.json`. Original PDFs are preserved.

The family installer builds both index sections and registers assets under `growing-food` and `repairs`. Updates are manual: from `/opt/dataark`, run `/usr/bin/python3 tools/install_family_resources.py --register`, then export intentional library changes with `venv/bin/python tools/content_profile.py export`. The family restore recipe checks both repositories before skipping a complete installed collection. Recipes and metadata are mirrored to the recovery kit and GitHub; large PDFs remain on the content drive.

## Verification

All fourteen PDFs passed header and pdfinfo checks. Every local PDF link, both landing cards, artwork and rendered documentation are checked after deployment. Content-profile tests cover missing gardening and repair assets and complete-collection reuse.
