# Forms and Templates

## Local access
Open `/library-files/forms/index.html` or the Forms and Templates landing-page card. The card has a collection link and a collapsed individual file list. Each installed document is registered in Manage Library and available through the existing HTTP, anonymous read-only FTP and read-only SMB content access.

PDFs open in browser PDF viewers. Word documents download for editing and printing in a compatible word processor. PDF interactive-field support is detected from the actual file; browser support varies. Download to a PDF application when necessary.

## Preserved editions
Federal tax set: 2025 Form 1040 and its instructions; Schedules 1, 1-A, 2, 3, A, B, C, D, E and SE; W-9, W-4, SS-4 and instructions, 4506-T and 8822. Year-specific return files are explicitly 2025 editions, not 2026 returns. Other forms retain publisher revisions at retrieval; inspect the source/revision details or document itself.

Other government forms installed: USCIS I-9 and instructions; GSA SF 95 (federal tort claim, with instructions). Massachusetts Form 1, its instructions and SSA SS-5 returned HTTP 403 and remain not downloaded. The original health-care proxy URL also failed; an alternate two-page Honoring Choices Massachusetts instructions/form (September 2025 English edition) is now installed. It permits reproduction in entirety with source/copyright retained and may not be resold. Follow its execution and witness instructions; this is not individualized legal advice.

Contracts installed: Common Paper Mutual NDA 1.0 (complete PDF and DOCX); Professional Services Agreement 1.1, Software License Agreement 1.1, and Business Partnership Agreement 1.1 (complete DOCX). Cover pages and standard terms are preserved together. Publisher files are unmodified and retain Common Paper attribution and CC BY 4.0 notices; the license text is local. The business partnership template covers referrals, co-marketing and sponsorships, not forming a legal partnership. Residential leases, personal loans and general bills of sale have not been added. Parties must choose governing law and transaction terms; the archive makes no jurisdiction-specific suitability claim.

## Privacy and use
Only blank public forms and templates belong here. Download a copy to your own device before entering personal information. The Ark has no form-completion upload or submission endpoint. Public content shares and staging shares should not hold completed returns, identification papers or signed contracts.

Filing requirements, accepted revisions, rates and addresses change. These are preserved reference editions. Check the required year, accepted edition and submission instructions before filing. A later tax-year return should be a separately labeled catalogue entry rather than silently replacing a previous year. This collection does not submit forms.

## Maintenance and rebuilding
Catalogue: `deploy/reference/forms-catalogue.json`. Installer: `tools/install_forms.py`. Downloads: `/mnt/storage/forms/`. Provenance: `sources.json`, containing original/resolved URLs, retrieval times, SHA-256, byte sizes, PDF page counts, field support and first-page revision text.

Run deliberately with caretaker filesystem privileges:

```sh
cd /opt/dataark
python3 tools/install_forms.py --register
bash deploy/deploy-web.sh
```

Requires Python standard library and Poppler `pdfinfo` / `pdftotext`. Downloads use three threads, a 30 MiB per-file limit and 45-second request timeout; no bandwidth cap. Validation checks PDF parsing, the stated 2025 tax year, excluded draft notices and complete contract DOCX cover/terms. Publisher files remain unchanged.

Failed publisher checks preserve a previously verified local file only if its hash matches the earlier provenance record. Per-file writes are atomic, followed by source records and generated index. Manifest registration holds the content updater lock. Failed downloads remain explicitly pending.

Update policy is **manual**; no scheduled refresh. Review catalogue additions and changed editions before running. Re-running deliberately reinstates removed catalogue files and re-registers successful downloads, so it must not be scheduled as a routine update. Ordinary file removal uses caretaker-protected Manage Library. One-click reinstatement for this file type is not implemented; use the installer and deploy commands. The collection index checks local inventory on load and disables links to removed files. Without JavaScript, static links may point at a subsequently removed file.

## Original sources
- IRS forms: https://www.irs.gov/forms-instructions
- Massachusetts DOR 2025 forms: https://www.mass.gov/lists/2025-personal-income-tax-forms-and-instructions
- USCIS I-9: https://www.uscis.gov/i-9
- GSA forms library: https://www.gsa.gov/forms-library
- Common Paper: https://commonpaper.com/standards/
- License: https://creativecommons.org/licenses/by/4.0/
