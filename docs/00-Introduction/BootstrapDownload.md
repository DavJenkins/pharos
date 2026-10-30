# Build a Data Ark

Turn a supported Raspberry Pi into a local knowledge appliance, then choose the content you want it to carry.

## Get the bootstrap

[Download bootstrap — Preview 2](https://github.com/DavJenkins/pharos/releases/download/bootstrap-2026.10.30-preview.2/data-ark-bootstrap-2026.10.30-preview.2.tar.gz)

**42.6 MB**, hosted on GitHub Releases. [Release notes](https://github.com/DavJenkins/pharos/releases/tag/bootstrap-2026.10.30-preview.2) · [SHA-256 checksum](https://github.com/DavJenkins/pharos/releases/download/bootstrap-2026.10.30-preview.2/SHA256SUMS)

Preview 2 passed an isolated deployment replay, 105 focused Python regressions, reader checks and caretaker authentication checks. See the [release audit](../20-Administration/ReleaseAudit.md). The earlier Preview 1 clean ARM64 installation and reboot results are separate evidence; Preview 2 has not repeated that full installation test.

## Start in three steps

1. Prepare Raspberry Pi OS 64-bit based on Debian 13 with the primary account named `admin`, plus an Ethernet or second-adapter internet connection.
2. Extract the kit onto a separate, already formatted content drive and open a local terminal on the Pi.
3. Run `sudo bash START-ARK.sh` to preview the plan, then `sudo bash START-ARK.sh --apply` to install.

Setup asks for confirmation and a private caretaker password. The installer does not format drives. See the [installation guide](../30-Developer/StockPiSetup.md) for mount ownership and the supported layout.

## Make it your Ark

The kit includes public source, readable configuration and the PMTiles tool. System dependencies are installed online. After setup, choose None, Minimal, Recommended or Full content; downloads use the Ark's connection and available storage.

Each appliance establishes its own private identity. Public configuration travels with the content drive, while household data and credentials stay separate. The local handbook remains available without internet access.

Preview release: physical spare-media acceptance remains separate.

## Explore

- [What the Ark can do](../10-User/FeatureCatalogue.md)
- [Engineering behind the Ark](../30-Developer/Engineering.md)
- [Uninterrupted installation results](../20-Administration/FrozenBootstrapReplay.md)
- [Source repository](https://github.com/DavJenkins/pharos/tree/feature/readme-foundation)
