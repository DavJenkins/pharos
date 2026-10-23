# Resources beyond the library

## A library with useful capabilities alongside it

The Ark exists to serve preserved content, especially under adverse conditions. Its computer, network, storage, tools and interfaces can also be resources for other tasks. They need not be useful only for maintaining the Ark. The goal is to make that utility accessible without sacrificing the local library.

Start with [the resource overview](/resources.html). Library use and public file copying require no caretaker account. Changing shared services, using a Linux shell, or placing private material on shared storage has different access requirements.

## Available on the current Ark

### Local network and browser services
The DataArk hotspot provides access to the library, maps, forms, documentation and local APIs without upstream internet. Open http://192.168.4.1/ if automatic portal discovery does not open the page. Power and working storage/network hardware are still required. This is not a configured mesh network, local chat system or general communications relay.

Internet pass-through can use the Ark's upstream connection for an individual hotspot device when upstream service exists. It does not create internet connectivity during an upstream outage. See [portal behavior](../20-Administration/Portal.md).

### File distribution and portable storage
Public library originals can be copied through HTTP, read-only SMB and anonymous read-only FTP. Authorized Linux accounts can use SFTP or rsync over SSH. A compatible computer can read the exFAT SSD after a clean Ark shutdown. Reader programs and their dependencies may still be needed. See [content access](/content.html).

These services can distribute an installed utility, document or data set to several people without a cloud service. They are not an unrestricted public upload area. Keep completed forms, passwords and private work off public shares. Household backups and staging have separate configuration and permissions; their existence does not establish that any new personal file is protected or backed up.

### General computing and terminal
Settings → System → Terminal opens the [HTTPS browser shell](../20-Administration/BrowserTerminal.md) using the existing Linux admin password. Normal SSH is also available to authorized Pi accounts. Shell access provides a general computer, not merely a dashboard control: users with authorization can work with local files, calculate, transform text/data, write scripts and troubleshoot connected equipment when compatible interfaces/tools are present.

The deployed Debian arm64 machine has Python 3, Git, tar, gzip, unzip, rsync, SSH, nano, GCC, make, curl and wget installed (checked October 23, 2026). Installed executables are not a guarantee that every Python library, compiler dependency or project SDK is available offline. Node.js and Vim were not found during that check. There is no preconfigured anonymous code-running service or per-user compute quota.

The browser terminal requires review of its local HTTPS certificate before entering a Linux password. The Linux admin account has its existing permissions, including sudo; it can affect everyone using the Ark. Use `exit` to finish. Do not run unknown programs, heavy compilation or large writes as though the appliance were a disposable workstation. This is operational guidance, not a claim of automatic workload isolation.

### Existing remote desktop and shell access
Inventory checked October 23, 2026, without changing these services:

- AnyDesk 8.0.4 is installed and its service is running. A successful desktop session and its available direct/offline connection path have not been verified in this review. A running AnyDesk service is not a promise of operation without vendor connectivity. Do not publish its access credentials or assume unattended access is configured.
- xrdp 0.10.1 and xorgxrdp are installed. The xrdp and session-manager services are running; RDP listens on TCP 3389. A compatible RDP client can target the Ark's current local address, subject to existing Linux login and session policy. Interactive desktop login, display availability and application usability remain unverified; do not call this a tested desktop just because the port is listening.
- OpenSSH server/client, SFTP, SCP and rsync are installed; SSH listens on TCP 22. This provides the existing authenticated remote shell and account-based file transfer.
- Classic `rsh`, `rlogin` and `rexec` executables were not found, and no listeners were found on their legacy TCP ports 512–514. They are not current resources. If “remote shell” is meant generically, SSH and the HTTPS browser terminal provide it.
- A legacy x11vnc unit exists but is failed; the x11vnc executable and VNC listener were not found. VNC is not currently usable. Repairing or enabling it is separate work, not something this inventory did.

AnyDesk/xrdp were already present before the browser-terminal work. No new remote-desktop access or authentication policy was enabled by adding this guide. Connections must use the actual available local network path; internet accessibility, router forwarding and offline behavior are not implied. For headless or low-resource use, the authenticated shell avoids needing a desktop session.

### Diagnostics, local documentation and source
System shows health, uptime and library capacity/activity. Debug adds bounded diagnostic information; Help and Developer API work locally. These may help investigate a failure or build a compatible local client. The API is not an unrestricted command-execution endpoint; management operations retain their own authorization.

The working source and maintenance tools are on the Ark at `/opt/dataark`, with the existing account-controlled source share. GitHub is an additional remote copy, not a runtime requirement. Local Git history, scripts and guides can support repair or adaptation even when the remote is unreachable. They do not provide a complete offline Debian package mirror or a tested clean-image bootstrap. See [source and handover](../20-Administration/SourceAndHandover.md).

## Potential resources — not configured capabilities

- A local notebook, message board or coordination app could use the existing browser/network platform. No such collaboration service is currently promised.
- USB devices, GPIO, a display or a keyboard could support local work, sensing or equipment interfaces, subject to actual hardware, power, drivers and testing. An available connector is not proof of an available function. No printer, radio gateway, sensor suite or GPIO control service is installed by this guide.
- Additional editors, conversion tools, packages or SDKs could broaden offline computing. Include their dependencies, licenses and working examples before marking them available.
- Shared writable workspaces or public compute could be useful. They need explicit storage, privacy, cleanup and resource policies; neither is enabled here.

## Adding a peripheral capability

Describe the adverse-condition use case, what is installed, how a user finds it, and what works without upstream connectivity. Identify the required account, equipment, power and storage. Prefer using an existing local tool before adding a continuously running service.

Preserve the hotspot, library readers and content storage. Consider CPU, RAM, I/O, free space and power, and avoid competing with critical service during a shortage. Quotas, isolation, stop controls and tested recovery must be deliberately implemented where needed; they cannot be inferred from this principle. Keep public reading independent of administrative or shell credentials.

Document installation, dependencies, usage, access rules, failure behavior and removal/recovery. Verify a real task offline, including dependency availability and recovery after interruption, before calling the new capability ready. Physical/electrical functions need separate checks. Do not infer certification, medical suitability or equipment compatibility merely because relevant reference material is present.
