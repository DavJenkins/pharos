# Publication edition discovery

Each installed publication keeps its exact source URL and hash. `deploy/reference/edition-discovery.json` separately describes a release family. It travels in public configuration bundles, the SSD mirror and recovery kits. No credentials, source documents or personal forms are added to the source repository.

The initial rules cover twelve saved IRS prior-year forms/instructions and the annual FCC Part 97 PDF. IRS uses a predictable filename in `irs-prior`; GovInfo uses the edition year in both the package directory and PDF filename. Tax year and annual edition are recorded separately from the date a file is published or retrieved.

## Rule example

```json
{
  "kind": "dated_template",
  "directory_template": "https://publisher.example/editions/{year}/",
  "filename_template": "guide-{year}.pdf",
  "period": "year",
  "period_kind": "annual_edition",
  "current_edition": "2025",
  "lookback": 2,
  "lookahead": 1,
  "max_probes": 4,
  "edition_text_pattern": "\\b{year}\\b",
  "action": "review",
  "retain_previous": true
}
```

Year, month and day periods support `{year}`, `{year2}`, `{month:02d}`, and `{day:02d}` in reviewed URL templates. Date windows and request counts are bounded; no URL-wide crawling or arbitrary sequence guessing takes place. `kind: index` with an explicit same-publisher `index_url` restricts probes to matching links actually listed on that HTML index. Prefer an index when it is available. JSON/RSS catalogue adapters are not part of this implementation.

A rule's current edition is a fallback: a matching installed source URL supplies its actual edition. Date placeholders may also occur in the first-page PDF edition-text pattern. Escape ordinary regex braces when using them alongside date placeholders. Review the publisher's actual first-page layout rather than assuming every printed year is the edition year.

## Verification and review

The existing weekly publisher checker also runs edition discovery. HTTPS redirects must stay on the configured public publisher host. Candidate responses are size-bounded (16 MiB by default), must be real structurally readable PDFs, and must identify the expected edition in first-page text. Draft/not-for-filing headers are excluded. A successful response or later-looking filename is not sufficient. Candidate records retain source URL, edition, byte count, SHA-256 and period meaning.

404/410 means no publication at that candidate URL; it is normal. GovInfo redirects missing packages to an HTTP-200 error page. Its explicit `not_found_title_pattern` recognizes only the verified `Page Not Found | GovInfo` title; other HTML/challenge pages remain errors. 403/429 and validation/network errors are reported as discovery issues and do not erase an already discovered candidate or installed content. Checks stop on publisher refusal/rate limiting. Rule checks follow a seven-day interval; retry-errors also retries failed discovery rules.

Manage Library shows a distinct **New edition available** result and a link to review that edition. It is not a queued download. These dated publications require caretaker review: tax forms, regulations and textbooks may need older editions retained alongside the new one. The current library path, manifest source, hash and publisher-check baseline are not silently replaced. Existing automatic Kiwix archive updates continue through their separate verified activation pipeline.

The discovery record is stored under its existing source entry in `/var/lib/dataark/reference-checks/state.json`. A later fixed-source check preserves that record. `tools/content_profile.py` includes the discovery configuration in portable exports. Adding a rule does not claim newer content exists; it describes how to look for it.

## Status-sync incident

The status endpoint now obtains CPU temperature from `/sys/class/thermal/thermal_zone0/temp`. The former `vcgencmd measure_temp` firmware-mailbox call entered uninterruptible kernel sleep, which also trapped subprocess timeout cleanup and exhausted status workers. The direct kernel sensor avoids that call. Old uninterruptible processes may remain until reboot; the API was restarted and its live status refreshes were verified separately.
