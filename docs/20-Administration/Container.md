# Run a Data Ark in Docker

A container Ark serves an external library on an existing local network, Wi-Fi or wired. It provides the dashboard, local files, maps and browser tools, ZIM/Kiwix reader, community board and banner, configuration inspection and validation, and content APIs. It starts no downloads. Installed content works without internet after the image has been built.

The container runs as UID/GID 1000, with Linux capabilities dropped. It needs no privileged mode, host network, physical devices or Docker socket. Networking, mounting drives, host software updates, optional HTTPS, FTP/SMB services, cloning and restoration are host responsibilities. Those appliance controls are unavailable in this deployment. Public media is mounted read-only; the community board and its banner remain writable in persistent state. The normal read-only internet-availability probe and an explicitly requested source-availability check are supported; neither installs content.

## Storage layout

| Storage | Container path | Purpose |
|---|---|---|
| Existing external library folder | `/mnt/storage` | Public documents, datasets and archives, read-only |
| Public configuration folder, optionally on the same drive | `/config` | Modular YAML and the compiled public manifest |
| Docker `state` volume | `/var/lib/dataark` | Community board, banner, events and operational state |
| Docker `private` volume | `/etc/dataark` | Caretaker password record; no shared default password |

Library and configuration paths must already exist on the Docker host. Compose refuses a missing bind source rather than silently creating an empty replacement. A remote Docker daemon uses its own filesystem paths. Docker Desktop requires sharing those host folders with its Linux VM.

The configuration folder must be writable by UID 1000. A copied Ark drive can supply `DATA-ARK-CONFIG/config`; its public collection is retained. A new empty configuration folder receives the image's public defaults on first start. Existing files are never replaced by a newer image's defaults. Container software comes from the image, never from Python or scripts found on a library drive.

## Build and start

Use the source checkout containing `deploy/container/compose.yaml`. Docker Engine/Desktop and Docker Compose must be installed on the host. Building the image requires internet for the base image, Debian packages and Python dependencies. The Dockerfile supports Linux ARM64 and x86-64 base images.

From the repository root, copy the example environment file:

```sh
cp deploy/container/example.env deploy/container/.env
```

Edit `deploy/container/.env`. Set `ARK_MEDIA` to the host's existing library folder and `ARK_CONFIGURATION` to its public configuration folder. For example, a Linux host might mount a drive at `/srv/ark-media` and use `/srv/ark-media/DATA-ARK-CONFIG/config`. These are examples, not required mount paths. Set `ARK_PORT` to a free host port and, when building a versioned image, set `ARK_REVISION` to the source Git commit.

```sh
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml build
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml up -d
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml logs -f ark
```

Open the Docker host's address at the chosen port, such as `http://ark-host:8088/`. Kiwix is available at `/kiwix/` on that same address and port. Registered archive links are adjusted automatically. Only configured, present ZIMs are loaded; older unregistered copies are not added just because they exist on disk. With no archives installed, the reader explains that state rather than failing startup.

The host port binds to all host interfaces by default. Choose `ARK_BIND=127.0.0.1` when placing a host-managed reverse proxy in front, or select a particular host LAN address. Use the host firewall and reverse proxy for access policy and trusted HTTPS.

## Caretaker actions

Browsing needs no password. Set the container's caretaker password privately in an interactive host terminal:

```sh
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml run --rm ark caretaker-password
```

This stores a salted password record in the private volume. It creates no Linux or root account password. Community moderation, board backup/restore and banner changes use the same caretaker prompt as the appliance.

Edit the mounted public YAML on the host, or copy configured content onto the library drive from the host. Choose **Container management → Reload public configuration and library**. It validates and renders the collection without downloading. Invalid edits retain the last working manifest and are reported in health. Modular YAML changes are also detected automatically; the container watches the configured archive set and refreshes its reader when files are added or replaced. A removed physical mount should be repaired on the host, then the container recreated to bind the intended media again.

The browser configuration editor supports reading and validation. Publication from that editor, content install/removal, browser download capture, physical-drive management and host password/network controls are not enabled in the container. They return an explicit host-management response rather than invoking sudo or systemd. The container management page explains the available workflow.

## Persistence and updates

Recreating the container retains configuration, media, community posts, banner and caretaker credentials. Back up the mounted public configuration and the two named volumes. Stop the Ark while making a consistent SQLite/state backup. Do not use `docker compose down -v` when you intend to retain those volumes.

To update software, build or select a reviewed image version, then recreate the container with the same mounts and volumes. No self-update or host installation is attempted from inside the container. Keep the previous image until the replacement passes its health check and content checks.

The public endpoints `/api/container/capabilities`, `/api/status`, `/api/integration/health` and `/api/library/changes` let local automation, including Home Assistant, inspect deployment capabilities, health and collection events. Container status describes its own network and services, not the host's Wi-Fi interfaces or systemd services. CPU/load and filesystem figures come from the container's Linux view; they are not a claim about a Raspberry Pi board's installed RAM.

See [platform flavors](../30-Developer/PlatformProfiles.md), [the public configuration interface](Configuration.md) and [community board](CommunityBoard.md).

Docker's [bind-mount documentation](https://docs.docker.com/engine/storage/bind-mounts/) explains host paths, read-only access and Docker Desktop behavior.
