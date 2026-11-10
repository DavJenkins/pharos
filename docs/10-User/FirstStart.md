# First start: choose your distribution path

There is one first-owner setup flow and one welcome-sheet template. Instructions vary with what you received; the private supplied-card sheet adds that device’s code and recipient details. The public guides do not contain private codes.

| What you received | Start here |
| --- | --- |
| Prepared microSD card | [Read guide](first-start/microsd.md) · [Printable PDF](assets/data-ark-first-start-microsd.pdf) |
| Complete appliance | [Read guide](first-start/appliance.md) · [Printable PDF](assets/data-ark-first-start-appliance.pdf) |
| Content drive / split Ark | [Read guide](first-start/content-drive.md) · [Printable PDF](assets/data-ark-first-start-content-drive.pdf) |
| Software / bootstrap kit | [Read guide](first-start/bootstrap.md) · [Printable PDF](assets/data-ark-first-start-bootstrap.pdf) |
| Linux LAN server | [Read guide](first-start/linux-lan.md) · [Printable PDF](assets/data-ark-first-start-linux-lan.pdf) |
| Docker / container | [Read guide](first-start/docker.md) · [Printable PDF](assets/data-ark-first-start-docker.pdf) |

## When a setup code is needed

The code protects an unclaimed device when someone sets its initial passwords through a network browser. It is pairing authorization, not a licence, subscription or internet activation. Prepared cards and appliances can supply the code privately. Trusted local installers and the Docker host terminal can set credentials directly, so those completed installs have no extra code step.

Any distribution that defers first-owner setup onto a shared network needs its own setup protection. A clone receives a new identity and code; it must not inherit a sender’s printed code or credentials. Codes are retired after successful setup.

## Two passwords, where applicable

On appliance and Linux-host deployments, the caretaker password authorizes web administration; the Linux admin password protects terminal and SSH access. They serve different roles and should differ. Docker creates a caretaker password for the container; Linux/host accounts stay under the host’s control.

See [setup security and offline reporting](../20-Administration/SetupSecurity.md).
