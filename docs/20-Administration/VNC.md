# VNC desktop access

## Connect
Use a VNC viewer supporting VeNCrypt / X509Plain or RSA-AES with Linux username/password. Host: `dataark` or `192.168.4.1` on the hotspot; TCP port `5901`. On the local LAN, use the Ark’s reachable hostname or its current private address. Some viewers need a separate port field or special explicit-port syntax; do not assume :5901 always means the same thing in every viewer. For TigerVNC, the explicit port syntax is `dataark::5901`; its [official viewer documentation](https://tigervnc.org/doc/vncviewer.html) lists X509Plain support. In RealVNC Viewer on the home LAN, enter `dataark::5901` (two colons); on the DataArk hotspot, use `192.168.4.1::5901`. Bare hostnames default to a different port unless the viewer connection profile overrides it.

Log in as the existing Linux desktop user `admin`, with its Linux password. This is not the shared caretaker password or the old standalone VNC password. No password was changed or recovered. PAM uses the existing `/etc/pam.d/wayvnc` policy, including the desktop-user check. The service shares the current logged-in desktop; it is not an anonymous desktop or a separate disposable workstation.

Review the locally issued certificate in the viewer. [Download the public certificate from the Ark you are using](../../legal/vnc-certificate.crt). Its identity and expiry are specific to that installation. Obtain the SHA-256 fingerprint and dates through the local console or an already trusted SSH session:

```sh
sudo openssl x509 -in /home/admin/.config/dataark-vnc/tls.crt -noout -fingerprint -sha256 -dates
```

Compare those values with the viewer before supplying a password. Use the configured hostname when a changed LAN IP is not covered by the certificate’s subject alternative names.

## What was repaired
The original x11vnc service failed because `/usr/bin/x11vnc` was missing. Installing it revealed that the active desktop is labwc/Wayland with Xwayland, not a full X11 desktop suitable for sharing with the old configuration. The repair uses native WayVNC 0.10.2 (Raspberry Pi package), retaining the existing logged-in desktop and port 5901. x11vnc 0.9.17 is now installed but its obsolete service is disabled; it may be useful for a future actual X11 session.

Verified October 23, 2026: custom service running, desktop output HDMI-A-2 at 1920×1080, listeners bound to the hotspot/current private LAN IPv4 addresses, RFB 3.8, VeNCrypt 0.2 with subtype 262 (X509Plain), and a certificate-verified TLS 1.3 connection. Anonymous and legacy VNC-password security types are not offered. The user subsequently confirmed RealVNC Viewer on Windows opened the desktop through both the local-LAN and DataArk hotspot connections. This verifies interactive login and desktop viewing through both routes. Keyboard/mouse operation, disconnected-upstream operation and reboot recovery were not separately confirmed.

## RealVNC Viewer compatibility

The explicit port matters: the server listens on 5901, not 5900. Windows successfully received an RFB 3.8 response from the Ark’s current LAN address on port 5901 while diagnosing a reported viewer timeout. This confirms the network path, not the address entered in the viewer or successful authentication.

RealVNC documents RSA-AES compatibility for WayVNC 0.7+ and requires an RSA private key setting. The installer now creates and preserves `/home/admin/.config/dataark-vnc/rsa_key.pem` and adds `rsa_private_key_file` to the private configuration. Linux PAM authentication and required encryption remain enabled. See [RealVNC's WayVNC connection guide](https://help.realvnc.com/hc/en-us/articles/14693032843293-Connecting-to-WayVNC-on-a-Raspberry-Pi-device-running-Wayland-using-RealVNC-Viewer). Do not disable authentication to work around a client mismatch. The user confirmed successful RealVNC desktop access through both the home-LAN and hotspot addresses on October 23, 2026. Its RSA server identity prompt must be reviewed by the user.

## Authentication and legacy compatibility
This configuration has enable_auth=true, enable_pam=true, relax_encryption=false and allow_broken_crypto=false. No stored password is copied into its configuration. The old `/home/admin/.vnc/passwd` file remains untouched and unused by this WayVNC service.

Clients lacking the supported encrypted Linux-login protocol are not compatible with this configuration. This does not establish a project-wide rule against legacy transports: adverse-condition compatibility may justify a separately scoped fallback, with explicit access, authentication and network requirements. See [resource design guidance](../10-User/Resources.md).

## Services, files and restart behavior
- `dataark-vnc.service`, running as admin, enabled at boot.
- `/usr/local/libexec/dataark-vnc`: a root-installed launcher that finds currently assigned RFC1918 IPv4 addresses on physical wl/eth/en interfaces and binds only those addresses. It fails/retries when none is present. Other interface naming schemes or public-address deployments require deliberate adaptation.
- `/home/admin/.config/dataark-vnc/config`: private mode 600, directory mode 700, no password; enables PAM and references local TLS certificate/key.
- TLS key/certificate and the persistent RSA-AES key: the same directory, mode 600. Only the public certificate is published. Existing pairs are preserved; incomplete pairs stop installation.
- XDG_RUNTIME_DIR=/run/user/1000 and WAYLAND_DISPLAY=wayland-0: this deployment's admin compositor socket. A new UID/socket or switch away from labwc requires reconfiguration.
- Frame rate capped at 15 FPS to reduce peripheral workload; it is not a CPU/memory quota. The service restarts after failure with a five-second delay. If the desktop/compositor is unavailable, VNC is unavailable too; the local library and SSH remain independent.
- Systemd read-only system/home protection, writable runtime directory and private-source network filter. NoNewPrivileges is intentionally not set: PAM's existing unix_chkpwd helper needs its normal group privileges to authenticate.
- Package-default wayvnc and wayvnc-control services are masked to avoid competing/default listeners. The old x11vnc unit is disabled. No new router forwarding or internet VNC access was configured.

The listener addresses are selected when the process starts. Restart it after a LAN/interface address changes. If the hotspot interface goes away, restore that network first; the library's manual address remains the preferred recovery route when available.

## Reproduce and recover
Tracked sources: `deploy/install_vnc.py`, `deploy/vnc/dataark-vnc.service`, and `deploy/vnc/launch_vnc.py`. This installer is for the existing admin/labwc deployment, not an arbitrary clean image.

```sh
sudo apt-get install --no-install-recommends wayvnc
cd /opt/dataark
sudo python3 deploy/install_vnc.py
bash deploy/deploy-web.sh
```

Confirm package authentication/PAM support before enabling on another distribution. The installer preserves a complete existing certificate pair. For renewal, replace both identity files deliberately, update the public copy and fingerprint record, and review the new certificate on clients.

```sh
systemctl status dataark-vnc.service
journalctl -u dataark-vnc.service
sudo -u admin XDG_RUNTIME_DIR=/run/user/1000 wayvncctl output-list
sudo systemctl restart dataark-vnc.service
```

Disable with `sudo systemctl disable --now dataark-vnc.service`. Do not enable the package-default services as a workaround. Local docs, SSH, RDP and AnyDesk are separate access paths with their own requirements.

Private configuration capture includes `/home/admin/.config/dataark-vnc`, `/etc/pam.d/wayvnc`, the launcher and systemd settings. Preserve those backups privately; never publish private TLS keys or desktop credentials.
