# System-card library and recipient setup

An Ark can serve useful offline content without an external drive. Its system-card library is an allocated ext4 image mounted at `/mnt/storage`, rather than another physical partition. Public source configuration remains intact.

## Capacity

Choose the library capacity during bootstrap with `--demo-library-gib`. Sizes from 2 to 1024 GiB are accepted when the underlying filesystem has enough free space, leaving at least 10 GiB for Linux. The actual card capacity is the practical limit. A 128 GB card can reasonably allocate 80 GiB for content.

Grow an existing owned, mounted image with:

```sh
cd /opt/dataark
sudo python3 deploy/demo_library.py --grow-gib 80
```

The grow operation verifies image ownership and the mounted loop device, allocates real space, expands ext4 online and updates its capacity record. It never formats existing content or shrinks the image. A failed operation retains a resize journal for inspection; do not delete the image to resolve a resize failure. Content hashes and available space should be checked after growth.

## Prepare this demonstration card for a recipient

The recipient setup tool currently supports the marked physical demonstration appliance. It preserves content and public configuration. It refuses configured integration/certificate credentials; those need a separate review before transferring an appliance.

Install the recipient API, setup page and helper from the same software revision before arming. Then run:

```sh
cd /opt/dataark
sudo python3 tools/prepare_recipient.py --arm
```

Confirm the preparation message. Securely supply the recipient the four-digit one-time pairing code stored in `/root/dataark-recipient-setup-code`, then shut down before mailing. Arming leaves the current running identity and provisioner SSH access intact until the next boot. At that boot the tool replaces the machine ID, hostname, Ark identity and SSH host keys, removes provisioner authorized keys and disables the provisioning cloud-init seed. Linux admin/root accounts are locked while setup is pending. The content library remains mounted and public browsing works.

The recipient connects to DataArk Wi-Fi, opens `http://192.168.4.1/` and follows the setup banner, or opens `/setup.html`. No monitor or internet is required. They supply the one-time code, a caretaker password for web controls and a separate Linux admin password for terminal/SSH access. Passwords require at least 12 characters. Five incorrect attempts cause a one-minute cooldown, retained across helper invocations. Leading zeroes are significant. The setup code is consumed after success and cannot change passwords again.

Root has no shared password and remains locked; direct root SSH is disabled. The recipient logs in as `admin` and uses `sudo`. The installed Pi OS sudo policy is retained. Password-based admin SSH becomes available after successful enrollment. Local desktop/terminal setup is also available.

The hotspot is open and the initial HTTP exchange is not encrypted. Perform initial enrollment privately, before inviting other users, or use the local terminal. Do not publish the one-time code in the public configuration or catalogue.

## Test record

On the physical test card, the system-card library was grown from 4 to 80 GiB. An isolated real ext4 image was first grown from 2 to 3 GiB and its sentinel hash remained unchanged. A physical reboot into recipient setup passed: the machine ID, hostname, Ark identity and SSH host keys were replaced; the provisioner key was removed. Browser API setup rejected five wrong pairing codes, enforced the cooldown, accepted the correct code afterward, and rejected reuse. The chosen admin password worked over SSH, the old SSH key was rejected, and root remained locked with direct root SSH disabled. No systemd units failed. The API was exercised from the desktop over the LAN; a phone connected through the hotspot is a separate client check. A real pseudo-terminal test confirmed that a waiting local password prompt closes when browser enrollment completes.
