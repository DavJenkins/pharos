# Data Ark container deployment

Run the Ark's public library and community services without a dedicated Pi OS installation. External content is read-only, public configuration is a writable bind mount, and private settings/state use separate persistent volumes.

Follow the [container guide](../../docs/20-Administration/Container.md). Copy `example.env` to `.env`, set existing host paths and run Compose from the repository root:

```sh
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml build
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml up -d
docker compose --env-file deploy/container/.env -f deploy/container/compose.yaml run --rm ark caretaker-password
```

Open the Docker host at the configured port (8088 by default). The reader is under `/kiwix/` on the same port. No host networking, privileged mode or Docker socket is needed. Network, disk, content acquisition and host software administration stay on the host.
