# Platform flavors and hardware discovery

The Ark is a Linux knowledge appliance. Raspberry Pi is its reference hardware rather than a requirement of its library or web application. The shared installer now uses small platform profiles, a command adapter and read-only discovery.

| Profile | Processor | Network behavior |
| --- | --- | --- |
| `raspberry-pi-debian13-arm64` | ARM64 | Raspberry Pi OS / Debian 13; reviewed `wlan0` hotspot and separate upstream. |
| `debian13-arm64-lan` | ARM64 | Debian 13; retains existing NetworkManager connections; no Ark hotspot or captive portal. |
| `debian13-amd64-lan` | x86-64 | The same LAN behavior on a desktop, laptop or server. |

The generic LAN profiles are experimental installation profiles. Their software checks do not replace fresh-machine and spare-media acceptance. The published bootstrap download remains the existing Pi preview; new profiles can be built from the feature branch without replacing that release.

## Common operating-system contract

The initial family is **Debian 13 and systemd**, with primary account `admin` at UID 1000, `/opt/dataark` for source and a separately mounted content drive at `/mnt/storage`. Existing unmanaged Ark installations, conflicting services and incompatible baselines are refused. Other distributions and 32-bit processors are not silently treated as compatible.

The hotspot profile requires NetworkManager, ethtool and iw. LAN profiles preserve the existing network manager (including systemd-networkd), do not install NetworkManager or dnsmasq, and require only iproute2 for initial read-only discovery. Optional discovery tools can add detail after installation without invalidating the LAN review. Missing prerequisites are reported before installation; discovery does not install packages, activate radios, scan for nearby networks or change connections.

## Discover and review

From the source checkout:

```sh
python3 deploy/bootstrap_stock_pi.py --list-profiles
python3 deploy/bootstrap_stock_pi.py --discover
```

Discovery records OS and processor, interface names/types, permanent hardware addresses where available, existing IP addresses/default routes and confirmed hotspot capability. It does not record Wi-Fi passwords or SSIDs. A wireless interface is not assumed to support hotspot mode merely because it exists.

The ordinary kit preview produces a proposed role assignment and an exact apply command:

```sh
sudo bash START-ARK.sh
```

Review the proposed interface identities, existing uplinks, network changes and public services. Run the generated command containing `--accept-plan` and `--apply`, then confirm `INSTALL`. A changed machine, hardware identity, upstream assignment, site settings or profile invalidates the reviewed plan. Normal DHCP address and link-state changes do not change its identity. An interrupted installation also checks the saved assignment before resuming.

LAN profiles keep the existing hostname and NetworkManager connections. They do not install Ark hotspot, captive-portal or internet pass-through rules. Docker and the public library services are still installed, so this is an appliance installation rather than a read-only application preview. Initial hotspot installation requires a local console; the LAN path may use an interactive SSH terminal.

The root-owned `/etc/dataark/platform.json` records the installed profile and discovered roles. LAN network controls are read-only in the Ark helper: changing connectivity remains an operating-system operation. Missing Wi-Fi or a deliberately absent hotspot is represented as **not configured**, rather than probing invented `wlan0`/`wlan1` devices. A corrupt platform record fails closed for network-changing actions.

### Multiple Ethernet connections

Discovery records all wired adapters, including wired bridge, bond and VLAN dependencies. The Ethernet popup has an adapter selector: each connection shows its own link state, addresses, gateway, permanent hardware address and default-route metric. Desktop hover text summarizes all adapters. The public network response exposes `ethernet_interfaces`; the legacy `ethernet` field remains a summary, preferring a connected, enabled default-route interface with the lowest route metric.

On the reference Pi, the switch affects only the selected adapter and retains its saved connection settings. Requests name both the interface and its permanent hardware address; changed hardware is refused. An older request without a selector is accepted only when exactly one wired interface exists. The helper protects the request's receiving interface and return route, including underlying bridge or bond members. If it cannot establish the access path, disabling fails closed. Generic LAN profiles remain read-only, and adapters without a verified hardware identity cannot be switched from the dashboard.

## Produce a flavor-specific kit

On the working Ark, preview first:

Checkpoint intended installer/profile code in Git before building. The builder refuses dirty or untracked installer code so its coordinator and committed source archive cannot silently disagree. Public content selections are exported separately; private configuration does not need to be committed.

```sh
cd /opt/dataark
sudo venv/bin/python tools/prepare_platform_kit.py --profile debian13-amd64-lan
```

Build after reviewing:

```sh
sudo venv/bin/python tools/prepare_platform_kit.py --profile debian13-amd64-lan --apply
```

Use `debian13-arm64-lan` or `raspberry-pi-debian13-arm64` for the other flavors. The command exports the current public recipe and committed source, obtains the profile's pinned PMTiles tool if necessary, and produces a `.tar.gz` archive plus SHA-256 under `/var/lib/dataark/platform-kits`. It includes no library payloads, credentials, saved network passwords or source-machine identity. It does not reconfigure the working Ark or replace the currently published download.

Each profile pins both its PMTiles archive/binary hashes and its architecture-specific Kiwix container digest. The official tool archive is bounded and verified before extracting the binary; ELF architecture is checked without running it. The recipient preflight rejects the wrong processor binary. Editing a Pi kit's label cannot turn its ARM binary into an x86 kit.

Cloning a drive retains the installed platform flavor by default. The generic kit producer lets the caretaker deliberately choose another flavor, independently of the source machine's processor.

## Adding another platform

Profiles live in `deploy/platforms/*.json`. `deploy/bootstrap_platform.py` owns discovery, architecture normalization, plan identity and the reviewed `debian-systemd-networkmanager` adapter. The shared coordinator remains `deploy/bootstrap_stock_pi.py` for compatibility with existing kit launchers. Software/content logic is shared rather than copied into a new installer per board.

A different Debian-compatible board can often use a generic LAN profile unchanged. Another operating-system family needs a reviewed command adapter and package/service mapping. Another processor needs verified tool and container pins. Another hotspot implementation needs an explicit network profile, capability checks and its own client acceptance. Profile JSON does not execute arbitrary shell commands.

Before declaring a flavor dependable, install it on fresh disposable media, interrupt/resume, reboot and verify mount identity, authentication, content readers, public access and preservation of existing connectivity. Radio/portal acceptance belongs to the profiles that actually configure a hotspot.
