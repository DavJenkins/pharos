# Browser terminal

## Access and login
Open Settings → System → Terminal. This opens `https://dataark:4200/` (or HTTPS port 4200 on the dashboard's current hostname/IP) in a new tab. The shell is fixed to the existing Linux **admin** account and asks for its Linux password. This is separate from the shared caretaker password. No password was changed, copied into the browser, stored in source, or made passwordless.

The authenticated session has the existing admin account's ordinary shell and sudo permissions. It can modify or erase Ark data. Type `exit` when finished. Closing a browser tab is not a substitute for deliberately logging out of a privileged shell. The user confirmed the terminal web interface worked at both https://192.168.4.1:4200/ (DataArk hotspot) and https://192.168.40.123:4200/ (home LAN) on October 23, 2026. Automated checks stopped at the password prompt without entering credentials. A specific command execution result, disconnected-upstream behavior and reboot recovery were not separately confirmed.

## First-use certificate trust
HTTPS uses a locally generated self-signed certificate for dataark, dataark.local, loopback, the hotspot address and local IPv4 addresses present when it was issued. Your browser may display a trust warning. Review certificate trust yourself before entering a Linux password; the agent must not bypass browser security interstitials.

The installed certificate's SHA-256 fingerprint is:

```text
EF:F6:4D:E5:E1:A1:1F:02:D7:83:06:75:A1:D3:B8:1B:A6:4D:6F:56:A1:03:C5:F3:0B:BE:B2:FE:4F:F4:1B:4B
```

Public certificate: [download](../../legal/terminal-certificate.crt). Confirm the fingerprint through this record or a trusted SSH connection, rather than trusting a certificate merely because the page offers it. It expires October 23, 2027. It is not installed into client trust stores automatically. If a new IP is not covered, use dataark or review/reissue the certificate with the additional SAN. Never switch the public terminal to plaintext HTTP to avoid a warning.

## Architecture and exact settings
- Debian shellinabox 2.21+b3. Cockpit was considered but was **not installed**.
- Apache HTTPS frontend on TCP 4200; TLS 1.2/1.3 only. Public plaintext requests are rejected. No port forwarding or external access was configured.
- Apache terminal access is restricted to loopback, RFC1918 IPv4, ULA IPv6 and link-local IPv6. This includes the DataArk hotspot and private home LAN. Private address ranges are not a replacement for authentication.
- Backend shellinabox listens only on `127.0.0.1:4201`. Its plaintext transport exists only on loopback, behind Apache TLS. The package's built-in TLS failed modern-client handshake tests; no TLS protocol downgrade was used.
- `dataark-terminal.service` runs as unprivileged shellinabox:shellinabox, with a fixed SSH command to `admin@127.0.0.1`; strict SSH host-key checks use locally copied host public keys. Password authentication was already enabled in sshd and was not broadened. No arbitrary SSH target, web root login or unauthenticated shell is offered.
- Systemd applies NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ProtectHome, a read-only known-hosts path, restricted address families and loopback-only network access to the backend process. Authenticated sessions are run by the existing SSH server with admin's normal permissions.
- The package's default `shellinabox.service` remains masked. Only the reviewed custom service is enabled at boot.
- Apache sends no-store, no-referrer and frame-denial headers. Terminal access logs omit query strings; request bodies, passwords and terminal output are not captured by the Ark Debug logger.

## Configuration locations
Tracked, non-secret sources: `deploy/terminal/dataark-terminal.service`, `deploy/terminal/apache-terminal.conf`, and `deploy/install_terminal.py`. The System link is in `app/static/assets/js/status-help.js`.

Live settings: `/etc/systemd/system/dataark-terminal.service`; `/etc/apache2/sites-available/dataark-terminal.conf`; `/etc/apache2/conf-available/dataark-terminal-listen.conf` (Listen 4200); `/var/lib/shellinabox/known_hosts`; `/etc/dataark-terminal/certificate.crt` and root-only `private.key`. `/etc/dataark-terminal` is root-only. Apache modules ssl, proxy, proxy_http and headers are enabled. Certificates/private keys must not be committed together or copied to a content share. Only the public certificate is published.

## Install, restore and certificate renewal
Install shellinabox from Debian with its default service masked, then run the reviewed installer with explicit enablement:

```sh
sudo systemctl mask shellinabox.service
sudo apt-get install --no-install-recommends shellinabox
cd /opt/dataark
sudo python3 deploy/install_terminal.py --enable
bash deploy/deploy-web.sh
```

The installer preserves an existing certificate/key pair and fails on an incomplete pair. It copies SSH public host keys, validates the service/Apache configuration, enables the custom service and reloads Apache. It never changes admin's password or SSH authentication policy. The --enable flag is required; installation is not automatic on a normal web deploy.

Before certificate expiry, have a caretaker replace the certificate/key with the required hostname/IP SANs, verify their match and update the public certificate copy and fingerprint record. Reload Apache and explicitly review the changed trust identity on clients. Restoring the private configuration snapshot retains the existing certificate identity; keep that backup private. `tools/capture_config.py` includes the private certificate directory, terminal unit, Apache settings and known-hosts file.

## Checks and recovery
Verified: Apache configuration syntax, TLS certificate validation using its explicit CA file, HTTPS 200, HTTP 400, backend loopback-only listener, default service masked, unauthenticated SSH denied and an actual HTTPS terminal session reaching the admin password prompt. No admin password was supplied during testing. The user subsequently confirmed the terminal web interface worked at both https://192.168.4.1:4200/ and https://192.168.40.123:4200/ on October 23, 2026. No particular command execution result was reported; command execution, disconnected-upstream behavior and reboot recovery remain separate checks.

```sh
systemctl status dataark-terminal.service
journalctl -u dataark-terminal.service
apache2ctl configtest
openssl x509 -in /etc/dataark-terminal/certificate.crt -noout -fingerprint -sha256 -enddate
```

To disable completely: disable the Apache terminal site/listen configuration and reload Apache, then stop the custom backend. Normal SSH and library services are independent.

```sh
sudo a2dissite dataark-terminal
sudo a2disconf dataark-terminal-listen
sudo apache2ctl configtest
sudo systemctl reload apache2
sudo systemctl disable --now dataark-terminal.service
```

Keep the package's default service masked. Re-enabling uses the installer. If a change breaks web access, recover through normal SSH or local console.

## Appearance

The browser terminal uses DEJ navy (`#102b43`) and warm gold (`#ead39b`), with a gold cursor and matching reconnect/menu controls. `deploy/terminal/dataark.css` changes default colours and readable monospace sizing; ANSI application colours and grid geometry stay under the terminal emulator. The installer copies it to `/etc/shellinabox/dataark.css`, referenced by the service `--css` flag. Refresh an existing terminal tab after a theme update. Restarting only `dataark-terminal.service` reconnects browser terminal sessions; the library and ordinary SSH service are independent.
