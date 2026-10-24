# Food preservation and emergency cooking

Open the **Food Preservation & Emergency Cooking** card on the landing page or the [local guide list](/library-files/family-resources/index.html#food-preservation). The [cookbooks and pantry meal plans](/library-files/family-resources/index.html#cookbooks) complement these references.

## Installed coverage

- USDA Complete Guide to Home Canning, 2015 revision: introduction and all seven numbered guides, including principles, fruit, tomatoes, vegetables, meat/seafood, fermented and pickled foods, and jams/jellies. Eight original PDFs, 197 pages.
- PNW 397, Drying Fruits and Vegetables, third edition, August 2009: 32 pages. Its stated dehydrator/oven methods and limitations remain unchanged.
- PNW 612, Storing Food for Safety and Quality, September 2009: 22 pages.
- USU Extension Emergency Food Storage booklet, copyright 2013: 120 pages.
- FDA Food and Water Safety During Power Outages and Floods, January 2023: four pages.
- FEMA / American Red Cross Food and Water in an Emergency, August 2004: 16 pages, explicitly labeled an archived edition.
- U.S. Fire Administration Grilling Fire Safety flyer: one page.

Total: 14 original documents, 392 pages. Source notices, complete procedures, equipment and altitude requirements remain in the originals. These are preserved publisher editions, not rewritten instructions. Historical storage recommendations and emergency advice retain their dates; the newer FDA outage guide is listed alongside the archived FEMA booklet. The pantry cookbook includes recipes using stored staples; none of these materials makes cooking fuel or unsafe refrigeration unnecessary.

## Sources and reconstruction

The USDA guide is hosted by the [National Center for Home Food Preservation](https://nchfp.uga.edu/resources/entry/about-the-usda-guide-to-home-canning-2015-revision); the drying and storage guides are university extension publications, and the outage and outdoor-fire documents are from FDA and USFA. Every file has its exact publisher URL and printed edition recorded in `deploy/reference/family-catalogue.json`. Installed file sizes, page counts, hashes and retrieval dates are in `/mnt/storage/family-resources/sources.json`.

Files are under `/mnt/storage/family-resources/food-preservation/` and available by HTTP, the public file share and anonymous FTP. The family resource installer registers them under the separate `food-preservation` repository. The `family` content-restoration recipe checks both repositories before deciding that an existing collection is complete. Thus a missing preservation PDF is not skipped merely because coloring books or cookbooks are present. The configuration mirror, recovery source kit and populated-drive replication include this collection through the existing family-resource paths.

To reconstruct explicitly, use the saved content profile and its `family` recipe. To refresh the publisher downloads and register current validated originals, run `/usr/bin/python3 /opt/dataark/tools/install_family_resources.py --register`, then deploy the web interface. This may download changed publisher editions; review and re-export the content profile after intentional updates. Downloads are manual, and older verified copies are retained if a publisher request fails.
