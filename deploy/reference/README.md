# Observed base configuration

These non-secret files record the deployed appliance reviewed October 22, 2026. They are reconstruction inputs, not an automatic clean-image installer.

- dataark.service: current loopback-only API service.
- apache-vhost.conf: port-80 static site and API reverse proxy.
- kiwix-compose.observed.yml: current Kiwix container configuration; latest is not an immutable image pin.
- boot-config.observed.txt: observed board/image boot settings, including conditional defaults that do not all apply to Pi 4.
- fstab-content.example: an explicitly incomplete example requiring the selected disk UUID and account IDs.

Review the documentation configuration reference and bootstrap plan before applying anything. Network profiles, actual credentials, SSH keys, Samba state and complete settings belong in protected configuration snapshots, not this directory. No install action is performed by reading these files.
