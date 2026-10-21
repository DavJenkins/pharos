# Local reference maps

The shared `geography` configuration selects Massachusetts, Worcester County (northern focus), and Middlesex County. Focus is descriptive; full county coverage is retained. Map collectors are separate from both Kiwix updates and household bugout tasks. They never emit HA emergency events or enter bugout jobs.

## Configured sources

- **Flood hazards:** the [MassGIS FEMA National Flood Hazard Layer archive](https://www.mass.gov/info-details/massgis-data-fema-national-flood-hazard-layer). This is the published **statewide** dataset, including mapped parts of both counties; it is not clipped to county boundaries. The source page currently describes July 2025 data. Do not confuse a recent download/check date with the dataset's effective date. Coverage gaps do not mean no flood risk. FEMA county download endpoints proved unreliable during verification, so the MassGIS distribution is used explicitly.
- **Property boundaries:** the official [MassGIS parcel download table](https://www.mass.gov/info-details/massgis-data-property-tax-parcels), joined by town ID to MassGIS municipality county membership. Only towns belonging to the configured counties are selected. ZIPs include GIS shapefiles and associated data; parcel lines are not legal surveys.
- **Topographic maps:** [USGS US Topo](https://www.usgs.gov/programs/national-geospatial-program/us-topo-maps-america), queried by county via The National Map API. All result pages are retrieved. The newest publication per geographic quadrangle is selected; shared sheets are deduplicated across counties. Sheets may extend beyond county/state lines. PDFs can be read or printed offline.

The verified October 14, 2026 plan contained **114 parcel ZIPs, 59 topo PDFs, and one flood ZIP**. Counts may change with coverage and publisher releases. These are downloadable GIS archives and PDFs; an interactive offline GIS viewer is not yet included.

## Configuration

```yaml
maps:
  enabled: true
  refresh_days: 30
  reserve_gib: 10
  max_run_gib: 8
  sources: [flood, parcels, topographic]
```

The sources adapter currently supports Massachusetts. County names come from `geography`, not hard-coded download lists. Changing geographic coverage or enabled source groups forces metadata rediscovery. Removed coverage is omitted from the new index; files are not automatically deleted.

Each source's metadata is checked every 30 days. The timer wakes daily to retry failed metadata or incomplete files. Conditional HTTP requests use ETag/Last-Modified so unchanged files need not be downloaded again. If a server provides no usable validators, its file must be fetched again to check it. A changed USGS release URL causes replacement even when the local filename stays the same.

Downloads are sequential, capped at 8 GiB of payload per invocation and 2 GiB per file, with a 10 GiB free-space reserve. Failed payload bytes also consume the invocation budget. Files exceeding the per-file cap need a deliberate implementation/configuration change; they are not silently truncated. ZIP integrity and PDF signatures are checked before atomic replacement. A failed replacement preserves the previous readable copy. The worker does not extract ZIPs or execute downloaded files. Newly downloaded bytes are hashed for identification; old content libraries are not rehashed.

## Install and publish

Run on the Pi:

```bash
cd /opt/dataark
venv/bin/python -m unittest discover -s tests -v &&
sudo python3 deploy/install_map_worker.py &&
./deploy/deploy-web.sh
```

The installer prepares pending-status pages, installs `dataark-maps.service` and its timer, and enables collection. The first collection starts about one minute later; existing API, content updater, Wi-Fi and backup services are not restarted. The new worker runs as admin with limited writable locations. The service is bounded to six hours per run; incomplete files retry on a later run. Partial map files restart from the beginning; this does not change Kiwix's existing download resume behavior.

The installed unit assumes `/opt/dataark`, `/mnt/storage`, and the admin account. The installer checks the configured mount before installation. It requires the existing venv dependencies, Python's standard library, systemd and runuser; no GIS runtime or spreadsheet package is needed for collection.

## Status and manual checks

Use **Local maps** near the bottom of the landing page. Its collection index links to Flood, Property, and Topographic pages, source attribution, file availability, saved/check dates, and errors. Archives are labelled **Download GIS ZIP**; PDFs are labelled **Open PDF**. The generated pages and files are portable when the SSD is mounted on another computer.

Direct browser status: `/library-files/maps/index.html`; machine-readable status: `/library-files/maps/status.json`. Map status is not yet part of the upper-right Kiwix sync indicator or the household HA sensor. HA can separately poll the map status JSON.

```bash
# Start a due check without waiting for the daily timer:
sudo systemctl start --no-block dataark-maps.service
# Check all metadata/files now (conditional requests still avoid unchanged downloads):
sudo -u admin /opt/dataark/venv/bin/python /opt/dataark/tools/map_worker.py --check-now
# Metadata-only plan: no map payload downloads:
venv/bin/python tools/map_worker.py --plan
# Inspect or pause:
systemctl status dataark-maps.service dataark-maps.timer --no-pager
journalctl -u dataark-maps.service -n 30 --no-pager
sudo systemctl stop dataark-maps.timer dataark-maps.service
```

A lock prevents overlapping manual/timed map runs. Source outages are reported individually and do not block other map collections. Existing good copies remain accessible. No public-data credentials are required.
