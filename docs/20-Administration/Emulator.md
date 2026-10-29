# Desktop ARM64 test Ark

The desktop test profile runs a software-emulated Ark on a Windows host. It uses QEMU's generic ARM64 `virt` platform with Cortex-A72 CPU emulation, four virtual CPUs, 4 GiB RAM and a 32 GiB copy-on-write system disk. It runs Debian 13 ARM64 and the Ark software; it is not complete Raspberry Pi 4 hardware emulation.

## Open and operate from the emulator host

These instructions run on the Windows computer hosting a prepared emulator, not on the Pi or an arbitrary computer viewing this handbook. Use the emulator folder chosen during setup; the examples below use paths relative to that folder.

Open PowerShell and select your prepared emulator folder:

```powershell
Set-Location (Read-Host 'Path to your prepared emulator folder')
```

Start the prepared guest:

```powershell
.\Start-Ark.ps1
```

From that same host computer, the dashboard is available at `http://127.0.0.1:18080/` and the reader at `http://127.0.0.1:18081/` while the guest is running. These loopback addresses do not open an Ark on another computer.

Connect over SSH:

```powershell
ssh -i ./seed/admin-ed25519 -p 22222 admin@127.0.0.1
```

Or open the prepared administrator shell:

```powershell
.\Connect-Ark.ps1
```

Stop the guest cleanly:

```powershell
.\Stop-Ark.ps1
```

The VM has its own generated SSH key and caretaker password. The latter is in `seed/caretaker-password.txt` inside the chosen emulator folder; keep that file and the SSH private key private. Linux SSH login is key-only. No production password, household configuration, Home Assistant credential or community database is imported. Community messages and any local banner changes belong to the guest's separate system disk.

Ports 22222, 18080, 18081 and the QMP control port 24444 bind only to desktop loopback. They are not LAN services. The guest has outbound NAT for package installation and can reach the Pi's media server. VM software/clock/virtual-network observations are not measurements of the physical Pi.

## Media access

The current guest mounts the physical Pi's `DataArk-Emulator-Media` Samba share at `/mnt/storage`, using a persistent read-only CIFS mount. The dedicated server share is also read-only, excludes hidden/private staging paths and disallows symlink following. The existing `Offline-Archives` share remains available read-only. `Bugout-Staging` is retained read-only; only the `dataark` development source share remains writable.

The VM reads the existing collection over the network; it does not hold another full copy. The Pi and network must remain available. This is not an offline-from-the-Pi acceptance test. A future local disk attachment or copy can replace this mount, but the same raw filesystem must never be writable by two independent operating systems simultaneously.

The guest mount uses `ro,nosuid,nodev,noexec`, SMB 3.0, and admin UID/GID 1000. `/etc/fstab` records automount and timeout behavior. Confirm with `findmnt /mnt/storage`; do not assume a visible empty directory means content is mounted. The eight registered ZIM archives are served by the guest's native `kiwix-serve.service`, not the production Docker container. Viewer links use the desktop-forwarded reader port 18081.

## Boundaries

`deploy/emulator/asgi.py` wraps the existing API. Public reads, configuration preview, local community changes and local Debug remain available. Media writes, publishing configuration, network controls, content installation/removal, recovery execution and household/bug-out actions are blocked with HTTP 409. No content-update, household or Home Assistant worker/timer is installed. The API service uses `NoNewPrivileges=true` and has no production root-helper permissions. There is no hotspot or real Wi-Fi adapter in this VM.

This profile is useful for interface/content-viewer development and read-only inspection. It does not replace physical-radio, portal, USB/power, spare-media or hardware-recovery acceptance. Hardware-related health warnings are expected rather than fabricated as successful probes.

## Source and rebuilding

Source profile: `config/emulator.json`; guest installer: `deploy/emulator/setup_guest.sh`; host seed/overlay generator: `deploy/emulator/prepare_host.py`; lifecycle scripts are in the same directory. The guest installer refuses an unmarked or non-QEMU/non-ARM64 machine and does not run the physical stock-Pi bootstrap. The prepared cloud-init seed supplies `/etc/dataark-emulator` and its unique administrator SSH key.

Initial preparation used checksum-verified QEMU for Windows 11.1.0 (the Windows build linked by qemu.org) and Debian 13 genericcloud ARM64. The QEMU installer SHA-256 is `f98a8aeb5f7faea9765b6dee28316c266cd179d80354a2fed8e50176f9a2e59f`; the Debian image was verified against its official SHA512SUMS. Downloads and launch arguments are retained in the VM directory. `prepare_host.py` requires `pycdlib`; it expects those verified binaries/image to exist and does not download or execute unknown installers. The original image stays unchanged; `disks/system.qcow2` is the writable overlay.

The guest source archive was built from the committed checkout, replacing the combined manifest with the API's public export. The existing Pi's ARM64 Python venv was copied as dependency software only; it contains no production credential/configuration files. Both use Debian 13 and Python 3.13.5. Revalidate interpreter/native-library compatibility when changing images. Shell scripts from Windows snapshots are normalized to LF inside the guest.

Guest installation expects `/home/admin/ark-source.tar.gz`, `/home/admin/arm64-venv.tar.gz` and `/home/admin/asgi.py`. Run `sudo env DATAARK_MEDIA_SHARE=//server/share bash /home/admin/setup_guest.sh`. Package prerequisites are Apache, Python 3/venv/YAML/Pillow, CIFS utilities, kiwix-tools, rsync, git, iw, NetworkManager and Samba. Software setup needs internet; a content drive alone is not an offline software installer.

## Verified

The ARM64 guest booted, mounted the real media read-only, and served the dashboard, API/status, handbook, Kiwix homepage and an actual Electronics Stack Exchange archive page. The national map archive returned HTTP 206 for a 16 KiB byte-range read. Household control requests returned HTTP 409. Loopback-only port bindings and absence of production download timers were checked. A guest reboot also returned all three services and the CIFS media mount read-only; the isolated profile tests passed again after reboot. Source changes still need normal regression and physical-device acceptance.

References: [QEMU ARM virtual platform](https://www.qemu.org/docs/master/system/arm/virt.html), [QEMU Windows downloads](https://www.qemu.org/download/), [Debian cloud images](https://cloud.debian.org/images/cloud/trixie/latest/).
