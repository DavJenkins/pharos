# Offline curriculum collection

The Learning & Homeschooling card includes the curriculum shelf at `/library-files/curriculum/index.html`. It preserves original English-language Core Knowledge PDF resources and live OpenStax books tagged for K-12 in the publisher catalogue. Source discovery is explicit; it does not scrape accounts, paid resources or instructor-only solutions.

## Coverage, not accreditation

`coverage.json` records discovered units, expected and installed files, teacher/student roles, subject and publisher grade labels. The table covers preschool, kindergarten and grades 1-12. High-school textbooks share a shelf rather than being arbitrarily assigned to a grade. A complete discovered package does not establish a complete subject-year or programme. An accredited school or credit-bearing service is not created by downloading books.

## Source and license preservation

Each original PDF is checked with `pdfinfo`, front-matter text inspection and SHA-256. Only files with an identifiable open license are published. Unknown licensing, broken PDFs and publisher errors remain visible as review items; staged failures stay outside public content. Core Knowledge licenses may require noncommercial use and share-alike. Preserve embedded notices and third-party credits. Review commercial redistribution separately; the public source repository contains the recipe, not these publisher PDFs.

## Rebuild and maintenance

`deploy/reference/curriculum-settings.json` records publishers, limits, language and reserve space. `curriculum-catalogue.json` records exact PDF URLs and unit/grade/subject contexts. `tools/discover_curriculum.py` discovers official public catalogue entries, caches pages and detects repeated pagination. `tools/install_curriculum.py --apply` acquires and validates the recorded files. `--index-only` regenerates the index from saved source records without downloading.

Discovery uses the Core Knowledge public WordPress library feed because the visible paginated download catalogue repeated its first page. OpenStax PDF URLs come from its public book catalogue. Files are bounded to 512 MiB, the collection to 40 GiB, and the drive retains a 40 GiB reserve. Three download workers share a request-start delay. Existing hash-verified copies are reused. The updater lock prevents competing library writes; logs are under the transient curriculum units and `/var/lib/dataark/curriculum`. These commands never remove saved content.

The content profile carries catalogue/settings files and source/coverage snapshots. Installed PDF sources and hashes are exported as direct-file restore jobs. The curriculum recipe regenerates the browsing index. Assets retain their source URLs for metadata-only scheduled publisher checks, avoiding repeated multi-gigabyte library downloads; a changed source is a review item, not an automatic replacement of teaching material.

## Khan Academy video and exercise archive

The English US-curriculum Kiwix archive is `khanacademy_en_all_2023-03.zim`, a March 2023 snapshot. The publisher metalink records **180,007,047,736 bytes (180.0 GB / 167.6 GiB)** and SHA-256 `3b8f4d286c6206a1c00c2252ac33187d30d4e146b8666ae2039d00f0d91eee3a`. The OPDS catalogue rounds its size slightly differently; exact file verification uses the metalink.

The manifest asset `khan-academy` belongs to the Learning & Homeschooling collection. The existing updater stages it under `/mnt/storage/.dataark-updates`, reports download/verification/activation progress, checks the complete size and SHA-256, then registers it in Kiwix. It is usable only after successful activation. An interrupted download retains partial data for a later run. Existing collections remain available during downloading; activation briefly restarts Kiwix.

Open it through the Learning card or the Kiwix library, selecting Khan Academy. It includes archived videos and exercises in mathematics, physics, chemistry, biology and history. It is not a current live Khan Academy account, school enrolment, or proof of complete K-12 coverage. Preserve the archive's own licenses and notices. Weekly publisher checks look for later editions; they do not promise weekly new content.

The public manifest and portable content profile retain the archive source, release series and checksum, allowing a replacement content drive to download it again. The large archive is not stored in Git. To inspect activity use `systemctl status dataark-update.service` and `/var/lib/dataark/updates/status.json`.

## Installation checkpoint: October 26, 2026

The PDF shelf contains **1,090 verified files: 1,026 Core Knowledge resources and 64 OpenStax textbooks**. Another 287 discovered files remain outside the published library because the automated front-matter check did not establish their open license. This is a review queue, not evidence that all 287 are prohibited. The collection inventory includes 1,392 assets with the Khan Academy archive. The permanent catalogue describes the completed collection; consult the dashboard for live installation and verification progress.
