# Source availability checks

Use **Check now** beside **Last checked** in the landing page's Content sources heading. Anyone who can read the dashboard can request this non-destructive check. It needs the Ark's upstream connection to reach publishers; it does not use the reader device's internet connection and never downloads or replaces library content.

The check runs in the API's background thread, with at most four concurrent publisher probes, a ten-second timeout per HTTP attempt, and one active sweep at a time. It uses HEAD and, for a publisher refusing HEAD with 405/501, a Range GET whose body is not read. A publisher may ignore that Range header; the client still closes the response without consuming its body. A sweep is limited to 2,000 configured assets and a one-minute interval between starts. There is no new periodic timer. Repeated clicks during a running sweep show that sweep rather than starting another.

The button shows progress while the page stays usable. On completion, the timestamp and per-file online source labels update in place. The timestamp retains its regular font, device timezone, and relative age. A failure preserves the previous complete cache and its timestamp. Network failures and blocked requests yield unknown observations, not proof that files are missing. 404/410 means unavailable at the checked URL; other HTTP errors are unknown. Successful source checks do not verify file identity, edition, or checksum, and are distinct from content updates and browser-capture comparisons.

Observations are stored atomically in `/opt/dataark/.cache/manifest-upstream.json`. The shared lock is `.cache/source-check.lock`. Both the web control and `python3 /opt/dataark/tools/check_upstream.py` use it. The page reads the latest observations on load, so a CLI check also appears after refreshing the browser. Regenerating the dashboard refreshes the static fallback too. Observations are runtime cache, not authoritative content configuration. Source URLs remain in `dataark.yaml` and the portable content catalogues.

API: GET `/api/sources/check` reads progress/results; POST with an empty JSON object starts a check. No arbitrary URLs, commands, or settings are accepted. Cross-origin browser requests are rejected. The worker is part of `dataark.service`; restarting that service interrupts an active sweep without replacing the old complete cache. Refresh and start again after a restart. No caretaker password, root helper, or extra package is needed.

Source: `app/services/source_check.py`, `app/routers/source_check.py`, `app/services/upstream.py`, `app/static/assets/js/source-check.js`, and the heading renderer in `app/services/manifest.py`. Tests cover job locking, cooldown, failed-check preservation, URL cache validity, bounded concurrency, progress, request restrictions, and manifest rendering. These sources and this guide are included in the recovery source kit and [GitHub repository](https://github.com/DavJenkins/pharos).

On narrow displays the source heading keeps the title and Check now button together on the first row. The smaller timestamp and status move below as a group when there is not enough room; they remain alongside the title on wider displays.

## Scheduled release-notice checks

The separate weekly reference-check worker can use an asset’s optional `source_check_url` instead of its download URL. This is useful for a pinned software archive whose new releases are announced in a small publisher manifest, such as the Ark bootstrap kit. The normal download URL and expected SHA-256 still identify the actual package; the notice has its own change baseline. A change is reported for review and never installs a replacement. This scheduled check is distinct from the heading’s immediate reachability sweep described above.

## Resolve a publisher change

Open **Manage Library → Source changes**. Select **Review on the Ark…** for the affected item. Caretaker authorization starts preparation: the Ark obtains the configured candidate, verifies it and presents the comparison. The installed copy remains available throughout preparation.

When preparation finishes, choose **Install verified candidate** or **Keep installed edition**. A dated publication can instead offer **Add [year] edition**; the earlier year remains a separate installed entry with its own local link. Keeping an edition acknowledges the exact inspected publisher version, not every future change. An unavailable publisher check remains an availability problem and cannot be cleared by pretending a download succeeded.

Supported adapters cover configured regional maps, FCC callbook data, PDF publications and HTML snapshots. Browser-only sources lead to [Capture a public download](BrowserCapture.md). Read the candidate identity before approving it; a different publication must not be imported as an identical edition.

Progress is retained if the dialog closes. Reopen the same review to see its latest state. Large maps can spend time planning, transferring and verifying; elapsed time and available transfer metrics distinguish these phases. Only one review worker runs at once. There is no FIFO waiting queue or browsable job-history screen.

The private latest-job records are under `/var/lib/dataark/publisher-review/`. Configuration rollback copies stay in its private `configuration-backups` directory; retained old content is separate from those credentials-bearing configuration files. Do not delete staging or recovery checkpoints while a review transaction is active.


## Unavailable or discontinued publishers

In **Manage Library**, choose **Source settings…** beside a failed publisher check, or under an installed item's **Update details**. The caretaker can pause checks, resume them, retire a source, or change its public HTTPS check/download URL. All actions retain installed files. Paused and retired sources remain listed under **Paused and retired sources**, with no active outage warning and no claim that the publication is current. A shared URL has one check policy for all references using it.

Failed automatic checks retry less frequently during prolonged outages: with the default weekly schedule, successive delays are 7, 14, 28 and at most 30 days. A successful check resets the delay. The last successful check remains visible. Manual retries remain available through publisher review.

Changing a source does not install its contents. Prepare and review a verified candidate before replacing the saved edition. Source policy and URL overrides are human-readable in `deploy/reference/reference-checks.json`, exported into the recovery configuration. Changes enter the collection lifecycle feed consumed by Home Assistant.

Saving also exports the recovery profile and its content-drive mirror. A failed export cancels the policy change and reports the cause; the previous policy remains active. Retry after correcting the reported problem. Generated recovery snapshots are rebuilt independently of editable configuration, so an obsolete generated snapshot does not require discarding or overwriting a person's configuration edits.

### Snoozing individual warnings

Choose **Snooze warning…** beside a source issue and enter a number of days. Retries continue, installed content stays available, and the source contributes no warning to the gear or content-card badge until the expiry time. If still unresolved at expiry, its warning returns automatically. **Snoozed warnings** in Manage Library lists these sources and their expiry dates. Set the duration to zero to end a snooze early. This differs from pausing or retiring a source, which stops automatic checks. Snoozes are shared across clients and included in recovery configuration and the Home Assistant lifecycle feed.
