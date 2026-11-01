# Ways to build or share a Data Ark

A Data Ark can be a home appliance, a portable library or a local-network service. Its delivery format determines what the recipient needs and whether installation requires internet access. These are ways to prepare and share an Ark, not a catalogue of units or cards offered for sale.

## A complete appliance

Supply a configured host, its system card or disk, and a populated content drive. The recipient supplies power and a phone or computer to browse. A Raspberry Pi hotspot configuration can serve nearby users without an existing router. A LAN installation serves an existing local network, Wi-Fi or wired.

A prepared appliance can start completely offline. It requires no online activation, registration or connection to a DEJ Software server.

## A ready-to-run microSD

Supply an installed microSD for a compatible Raspberry Pi, with a useful selection of content stored on the card itself. The recipient needs the Pi, a suitable power supply and a browser device. An external content drive is optional.

The system-card library has an explicit capacity, preserving room for Linux and updates. The demonstrated 128 GB card allocates 80 GiB to its library; allocation does not mean that the library is full. Content selection and available space are specific to each card.

A prepared card can start and serve its installed collection without internet. The demonstration selection includes the Wikipedia 100-article sample and the collection and feature guides, not the full collection described in the catalogue.

### First-owner setup without a monitor

The sender prepares the card for its recipient and supplies a four-digit one-time pairing code. The first recipient boot establishes a new hostname, machine/Ark identity and SSH host keys and removes the provisioner's SSH access.

Connect to DataArk Wi-Fi and open `http://192.168.4.1/`. Follow the setup banner, enter the code, and choose a caretaker password for web management and a separate Linux admin password for SSH/terminal access. Both passwords require at least 12 characters. Five wrong codes impose a one-minute cooldown. Successful setup consumes the code. Browsing remains open without a password.

There is no shared root password. Root stays locked and direct root SSH is disabled. The recipient uses the `admin` account and `sudo` for Linux administration. Local desktop/terminal setup is also available. Initial hotspot/HTTP enrollment is not encrypted; complete it privately before inviting other users.

[Download the printable microSD quick start (PDF)](assets/data-ark-quick-start.pdf). Its code field is intentionally blank; the sender supplies the code for that particular card. Keep card-specific sheets containing real codes private.

## A populated content drive

Supply the content and public configuration together with the recovery kit. Portable documents and compatible offline archives can be used without rebuilding the original appliance, using suitable readers. Installing the full Ark on a supported Linux host currently needs internet to acquire system packages and other software dependencies. A populated drive is not, by itself, a preinstalled operating system.

## A software-only download

The [bootstrap kit](../00-Introduction/BootstrapDownload.md) supplies software and readable public configuration. The recipient supplies a supported Linux host, storage and internet for installation and content acquisition. The kit is not a disk image and does not include the full library. Its published release and installation instructions identify the supported platform.

Once installed and populated, the Ark serves local content offline. Configuration can also travel without content, preserving the reference list and the desired collection for later acquisition.

## An entirely offline demonstration

For a recipient who does not want the device online, supply a prepared appliance or microSD with the desired content already installed. Do not connect Ethernet or configure upstream Wi-Fi. Phones can join the Ark hotspot and read the local collection without internet or online activation. Wi-Fi clients may need to accept the network's "No internet" warning; turn off cellular data when demonstrating offline operation.

Offline is different from radio-silent: a hotspot broadcasts nearby. A wired deployment can avoid Wi-Fi broadcasting. Connecting a prepared Ark to the internet is a choice for acquiring content and updates, not a condition for using its installed library.

See [system-card library and recipient preparation](../20-Administration/SystemCardLibrary.md) for administration and the physical test record.
