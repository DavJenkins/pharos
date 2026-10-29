# Build a Data Ark

Turn a supported Raspberry Pi into a local knowledge appliance, then choose the content you want it to carry.

## Get the bootstrap

[Download bootstrap — Preview 1](https://github.com/DavJenkins/pharos/releases/download/bootstrap-2026.10.29-preview.1/data-ark-bootstrap-2026.10.29-preview.1.tar.gz)

**42.1 MB**, hosted on GitHub Releases. [Release notes](https://github.com/DavJenkins/pharos/releases/tag/bootstrap-2026.10.29-preview.1) · [SHA-256 checksum](https://github.com/DavJenkins/pharos/releases/download/bootstrap-2026.10.29-preview.1/SHA256SUMS)

The corrected kit completed a clean ARM64 installation in one run, with 43 regression tests and successful service, file-sharing, authentication and reboot checks.

## Start in three steps

1. Prepare Raspberry Pi OS 64-bit based on Debian 13 with the primary account named `admin`, plus an Ethernet or second-adapter internet connection.
2. Extract the kit onto a separate prepared content drive and open a local terminal on the Pi.
3. Run `sudo bash START-ARK.sh` to preview the plan, then `sudo bash START-ARK.sh --apply` to install.

Setup asks for confirmation and a private caretaker password. The installer does not format drives. See the [installation guide](../30-Developer/StockPiSetup.md) for mount ownership and the supported layout.

## Make it your Ark

The kit includes public source, readable configuration and the PMTiles tool. System dependencies are installed online. After setup, choose None, Minimal, Recommended or Full content; downloads use the Ark's connection and available storage.

Each appliance establishes its own private identity. Public configuration travels with the content drive, while household data and credentials stay separate. The local handbook remains available without internet access.

Preview 1: physical Pi validation is the next step.

## Explore

- [What the Ark can do](../10-User/FeatureCatalogue.md)
- [Engineering behind the Ark](../30-Developer/Engineering.md)
- [Uninterrupted installation results](../20-Administration/FrozenBootstrapReplay.md)
- [Source repository](https://github.com/DavJenkins/pharos/tree/feature/readme-foundation)
