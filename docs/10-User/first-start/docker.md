# First start: Docker / container

[Choose a different distribution path](../FirstStart.md) · [Download printable guide](../assets/data-ark-first-start-docker.pdf)

The container serves a library on an existing local network using host-mounted media and persistent state. It does not manage the host's radios, disks, root account or power.

## What you need

- Docker Engine or Docker Desktop with Compose.
- An existing library folder, a writable public configuration folder and persistent private/state volumes.

## First start

1. Follow the Container guide. Set ARK_MEDIA, ARK_CONFIGURATION and ARK_PORT in the supplied Compose environment file.
2. Build or select the reviewed image, then start it using the documented Compose command. Building needs internet; reading installed content does not.
3. Set the caretaker password using the documented caretaker-password command in the host terminal. No first-owner pairing code or Linux admin password is created by the container.
4. Open the host address and selected port in a browser. Keep the same media/configuration mounts and private/state volumes when recreating or updating it.

## Setup authorization

Set the caretaker password in the Docker host terminal using the documented caretaker-password command. The container does not use pairing codes or create Linux admin accounts.

No online activation, DEJ Software account or registration is required. A new recipient gets a fresh identity and code rather than inheriting the original owner’s credentials.

## Hardware and operating notes

- Networking, physical drives, host credentials, power and optional HTTPS are host responsibilities.
- Do not delete the private/state volumes when you intend to preserve passwords, posts, banner and operational state.

## Further help

- [Installation and bootstrap](../../30-Developer/StockPiSetup.md)
- [Container deployment](../../20-Administration/Container.md)
- [First-owner setup security](../../20-Administration/SetupSecurity.md)
