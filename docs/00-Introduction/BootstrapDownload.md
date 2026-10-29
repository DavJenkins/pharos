# Download and build a Data Ark

The recovery process is the foundation for a downloadable Data Ark bootstrap: start with a supported operating system and a prepared content drive, then install the Ark software and restore an explicitly selected library.

## Bootstrap release status

**A supported downloadable bootstrap has not been released yet.** The corrected kit has passed an uninterrupted clean Debian 13 ARM64 software-phase replay, including service, authentication, file-sharing and reboot checks. Physical Pi networking, local-console installation and spare-media acceptance are still pending. The experimental source is available for developers; it is not a certified ready-to-run appliance installer.

## What the first supported download will provide

- A versioned public source and configuration kit, a manifest and checksums.
- Supported operating-system, architecture, account and storage requirements.
- A preview before installation and explicit authorization for system changes.
- Separate content presets with capacity checks and explicit download approval.
- Instructions for validation, recovery and preparing another configuration-only or populated drive.

The kit does not include private household data, appliance passwords, SSH host keys or a shared device certificate. A new Ark establishes its own private identity. Preparing or formatting a disk is a separate explicit operation.

## What remains available offline

Each Ark carries documentation matched to its installed software. Public website editions supplement those local copies. Website publication does not cause an older Ark to download newer operational instructions independently of a software upgrade.

The configuration registers this documentation shelf and stable local addresses. Its pages are generated from repository sources during software publication, rather than being removable publications managed by the content downloader.

## Installation and evidence

- [Stock-Pi setup guide](../30-Developer/StockPiSetup.md)
- [Uninterrupted frozen-kit replay](../20-Administration/FrozenBootstrapReplay.md)
- [Clean-OS software test](../20-Administration/CleanBootstrapTest.md)
- [Recovery acceptance results](../20-Administration/RecoveryValidation.md)
- [Engineering behind the Ark](../30-Developer/Engineering.md)
- [Experimental source repository](https://github.com/DavJenkins/pharos/tree/feature/readme-foundation)
