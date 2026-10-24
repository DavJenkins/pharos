# Sanitation and hygiene during utility outages

Use the **Sanitation & Hygiene** card on the landing page or the [local sanitation guide list](/library-files/family-resources/index.html#sanitation).

## Installed coverage

Twelve original documents, 47 pages:

- Oregon State University Survival Basics: Sanitation and Waste Management, EM 9334, October 2021 (6 pages).
- RDPO Emergency Toilet Guidebook, updated February 2025 (9 pages).
- RDPO Twin Bucket quick leaflet (1 page), English bucket labels (2 pages) and Spanish bucket labels (2 pages).
- Siphon-pump handwashing station plan by Brian Dobecki / Washington County Medical Reserve Corps, September 2016 revision (2 pages).
- UNICEF Tippy Tap field demonstration guide, May 2020 (16 pages).
- CDC Keep Calm & Wash Your Hands reminder poster, archived campaign edition (1 page).
- CDC / EPA / FEMA / HUD Homeowner’s and Renter’s Guide to Mold Cleanup After Disasters, June 2015 (4 pages), plus the CDC mold-cleanup shopping list (1 page).
- Washington DOH Safely Cleaning Up After Rodents, January 2024 (1 page).
- San Diego County rat prevention and control brochure (2 pages).

These preserve original publisher procedures, credits and limitations. Pacific Northwest toilet guidance is identified as regional, not permission to dispose of waste in a particular way in Massachusetts or elsewhere. Local public-health, wastewater and waste-collection instructions govern disposal. The UNICEF file retains its 2020 campaign context; it is included for the illustrated handwashing-station construction material. Cleanup references retain their original re-entry and protective-equipment guidance.

## Provenance and reconstruction

The readable source catalogue is `/opt/dataark/deploy/reference/family-catalogue.json`. Originals live under `/mnt/storage/family-resources/sanitation/`. The main `family-resources/sources.json` records exact source and resolved URLs, retrieval times, page counts, sizes, hashes, editions and use notes.

CDC blocked several direct downloads from the Ark. The original multi-agency cleanup guide was obtained from EPA, its shopping list from Winnebago County Health Department, and the CDC reminder poster from the Global Handwashing Partnership. Rodent prevention comes directly from San Diego County and the cleanup handout directly from Washington DOH. The guidebook and labels use the public files linked by RDPO, without authentication or account access.

The family installer registers these files under the separate `sanitation` repository. The family restoration recipe checks this repository alongside family resources and food preservation, so missing sanitation files trigger restoration even when coloring books remain present. Existing verified files are retained if publisher downloads fail. Configuration-only reconstruction and populated-drive replication use the existing family-resource paths; no private household information is included.

To rebuild publisher downloads explicitly, run `/usr/bin/python3 /opt/dataark/tools/install_family_resources.py --register`, then deploy the web interface. Review edition changes and re-export the content profile after intentional updates. The saved source/profile is mirrored on the content drive and included in the public recovery kit. All downloads are manual.
