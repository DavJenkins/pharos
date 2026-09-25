# Central asset manifest (v1.4)

The landing page is generated from `/opt/dataark/dataark.yaml`. Each enabled repository creates one card; assets belong to a repository through `repository_id`. Categories group cards; asset categories can differ from their parent's category. Scenarios and tags describe intended uses.

Edit the YAML, then run `./deploy/deploy-web.sh` from `/opt/dataark`. Deployment validates and renders the manifest before copying the website. To render without deployment, run `bash tools/render_dashboard.sh`. The Bash entry point uses the existing virtual environment and Python/PyYAML/Pillow, with no jq or yq dependency.

The default file lists six content sources in one Content sources group and identifies six known local files. Local availability is independent of that grouping. The Raspberry Pi logo appears separately in the template as a platform credit, not a content repository. `examples/manifest-v1.4.yaml` is a separate illustration with ZIM, PDF, and portable binary entries. Its example.invalid URLs and sample filenames must be replaced before use. An empty `repositories: []` and `assets: []` is valid. Remove entries you do not want displayed; files on the SSD are never deleted by this process.

## Configuration fields

- `system.version`: the quoted string "1.4".
- `system.project_name`: page title.
- `system.base_mount`: absolute path containing content, currently `/mnt/storage`.
- `system.hide_missing`: false by default; true hides locally missing assets and repositories whose registered assets are all missing. Reference-only repositories remain visible.
- `system.services.kiwix_port`: local reader port, default 8080. Service links use the browser's current hostname, supporting either network interface.
- `system.services.content_url_prefix`: deployed static file alias, currently `/library-files/`.
- `system.services.samba_share_path` and `web_root`: descriptive metadata; changing them does not reconfigure Apache, Samba, or mounts.
- `repositories`: unique `id`, `title`, `category`, optional `description`, `enabled`, `artwork`, `links`, `tags`, `scenarios`, and update metadata.
- `assets`: unique `id`, `title`, `repository_id`, `category`, and `relative_path` beneath the content mount. Optional descriptive fields include `subcategory`, `architecture`, `executable`, and size estimates. Actual file size is reported separately in generated metadata.
- `links`: a title and URL, or `service: kiwix` with a root-relative path. Set `requires_internet: true` on online reference links. Root-relative URLs are preferred for local services.
- `service_endpoint`: an optional additional reader URL for an asset; the original file download stays available. Executable metadata never causes a program to run.

The validator rejects duplicate keys/IDs, dangling references, path traversal, unsafe URL schemes, malformed artwork, and unsupported versions. Edit the template in `app/templates/index.html` for page structure; the static index is generated.

## Artwork

`artwork` is supported on system (background), repository, and asset entries. Supply exactly one of `path`, `url`, or `inline`, plus optional `alt` text.

- `path` is relative to the directory containing the YAML manifest and must remain within it.
- `url` is HTTP(S). The first build fetches the image and stores a persistent copy in `.cache/artwork/`. Later builds reuse it offline. Run `bash tools/render_dashboard.sh --refresh-artwork` to refresh; a failed refresh retains a valid cached copy. A new URL without a cached image must be reachable for its first build.
- `inline` is a complete base64 data URI, such as `data:image/png;base64,...`.

Supported formats are PNG, JPEG, GIF, and WebP, limited to 5 MiB and 25 megapixels. SVG is not supported. All rendered artwork uses local copied files under `assets/manifest/`, including remote images. Browsers do not contact the artwork source. Artwork cache filenames use hashes; this does not checksum content archives.

## Local and upstream availability

A render checks whether each registered local path exists. Missing items remain visible with an Unavailable / Pending Download badge unless hide_missing is enabled. No payload is read or checksummed. Availability reflects the last render: rebuild after adding/removing content. The independent portable SSD catalog still uses `python3 tools/publish_content.py`; it includes discovered files, while dashboard cards contain only registered assets.

Upstream status is independent. It is unknown until checked manually or by the automatic worker. Add verified asset `download_url` and optional `mirror_url`, then run `venv/bin/python tools/check_upstream.py` when online. Rebuild/deploy afterward to display the results. Exact-version download URLs are configured for the current collection. The automatic worker refreshes observations after each successful discovery/update cycle.

Checks use HEAD, with a Range GET fallback for servers rejecting HEAD. Response bodies are not read. HTTP 2xx indicates availability at that time, not verified identity or integrity; 404/410 indicates that configured URL was unavailable. Authentication failures, rate limits, server failures, and network failures leave status unknown. One available mirror is sufficient; source unavailable requires every configured source to return 404/410. This is an observation, not proof of permanent removal.

Results are dated and stored in `.cache/manifest-upstream.json` separately from user configuration. A changed source URL invalidates its old observation. No background asset-source probes run during rendering or browsing. No asset sources configured means no asset-source probes. The separate browser connectivity check described below does not change these observations.

A local file whose sources are unavailable is shown as Preserved locally — source unavailable. It remains accessible and is never hidden or deleted because of upstream status. This status refers to the last recorded check. hide_missing only applies to local absence.

## Update policies and checksums

Repository policy values are inherited by assets unless overridden. Accepted `update_policy` values are manual, auto, pin_version, and on_network_available. `refresh_interval` accepts never or durations such as 30d. pin_version requires a `version_pin`. The installed automatic worker honors these policies for configured kiwix_zim sources, as described below. Manual entries are not downloaded automatically.

`expected_hash` may contain a 64-character SHA-256 digest supplied by a trusted source. It is optional metadata, not an instruction to hash the library. Existing portable catalog checksum generation remains an explicit `tools/publish_content.py --checksums` option.

## Browser connectivity and navigation

The dashboard header provides Access your content. Network settings and sync status are in the status bar. External repository links marked requires_internet and the Raspberry Pi platform credit are disabled while checking connectivity or when the browser internet check fails. Local library and administration links remain available. Without JavaScript, online links remain normal labeled links.

The browser checks its own internet access, independently of the Ark adapters, on page load, browser network changes, return to the tab, and every 60 seconds while visible. Check internet retries immediately. It fetches a small HTTPS resource at www.gstatic.com/generate_204, falling back to en.wikipedia.org/favicon.ico, with a four-second timeout per attempt, no credentials, no referrer, and no cache. These requests reveal the browser's public IP to the probe host. A successful request establishes general reachability, not that every external destination is working; a firewall blocking both probes can also cause Internet unavailable. The browser's offline indication disables external links immediately.

Connectivity does not mark an archive source as removed or affect local copies. Source availability still comes from explicit dated checks. To run the browser behavior checks where Node is installed, use `node tests/connectivity.test.js`.

## Automatic content processing

Install once on the Pi with `sudo python3 deploy/install_update_worker.py`, then restart `dataark.service` after deploying the updated API code. Installation enables dataark-update.timer. The timer polls every five minutes; the asset refresh_interval controls when release discovery is due. The five registered ZIM series use on_network_available with a one-day interval. Newer releases are discovered dynamically from the official Kiwix index; the dated one-time JSON update plan is not used by the worker.

Each automatic asset requires update_source with kind: kiwix_zim, directory (the official wikipedia or stack_exchange download directory), and filename_prefix identifying its exact series. This first adapter handles those ZIM archives. The Windows reader remains manual; automatic ZIP installation and other provider adapters are not yet supported. Reference-only cards never trigger speculative downloads.

Policies: manual skips downloads; auto and on_network_available process due assets and retry interrupted transfers when access returns; pin_version selects exactly version_pin such as 2026-08. A refresh_interval of never disables discovery. Disabled repository entries are skipped. Without an explicit pin the worker does not downgrade a newer local archive.

Downloads resume in /mnt/storage/.dataark-updates. The existing staging script uses the same lock, so the worker waits if that one-time operation is running. Staged files matching a discovered release are reused after validation. The worker checks mount, space (with a 2 GiB reserve), size, ZIM header, and publisher SHA-256 for new downloads. It does not checksum the existing library or generate catalog checksums.

Activation reuses the transactional activation tool, with a dynamically generated per-asset plan. It briefly stops Kiwix, moves any previous version into a hidden recovery folder, installs the verified archive, starts Kiwix and verifies the expected catalog entry. It updates the manifest filename, title date, source URL and expected_hash, regenerates the portable catalog, and deploys the dashboard. Old versions are removed only after successful activation and publication. Interrupted pre-commit switches are rolled back on the next worker run; committed switches finish publication and cleanup. Persistent faults remain visible as Update failed and in the service journal.

Progress is stored in /var/lib/dataark/updates/status.json. The API reads it without Docker privileges and reports checking, downloading with percentage, verifying, activating, publishing, waiting, or failed. A stopped worker with old in-progress telemetry is reported as stale rather than indefinitely downloading. Upstream availability observations are refreshed and the dashboard republished after successful cycles.

Operational commands:

- Logs: `journalctl -u dataark-update.service -f`
- Current service: `systemctl status dataark-update.service --no-pager`
- Run a due check now: `sudo systemctl start dataark-update.service`
- Pause immediately: `sudo systemctl stop dataark-update.timer dataark-update.service`
- Resume: `sudo systemctl start dataark-update.timer`
- Disable future automatic runs: `sudo systemctl disable --now dataark-update.timer` (stop the service too if it is currently running).

The worker service is privileged because it must restart Docker and publish the site. Installation does not grant the web API Docker or download privileges. Keep repository and manifest edits restricted to trusted administrators. API responses include status.update for progress detail. Unit tests use mocks and temporary files; live systemd activation must be verified on the Pi after installation.

## Reading links and archive downloads

Asset titles for ZIM files open the corresponding local Kiwix reader. The optional online_url field supplies the external reading-page link beside the title; download_url and mirror_url are retrieval metadata for updates and are never used as that external link. Missing archive releases do not disable an independent online reading page. Archive downloads remain available through the explicitly labelled content catalog and file browser.
