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

## Add an external drive

From **Manage Library → Add or change a content drive**, choose the system-card migration link to open **Use an external library drive**. Connect an empty, formatted USB drive, choose **Find drives**, select it, and choose **Preview transfer**. These operations use the on-demand caretaker prompt and its optional password cache.

The transfer copies existing installed content rather than downloading it again. A saved older edition is copied too; being due for a publisher check does not make it unusable. After the switch, normal publisher checks can offer newer editions, and missing selections can be restored separately. The transfer itself needs no internet connection.

For an empty drive in the general **Library storage** workflow, **Copy and verify the existing library before switching** is selected by default when the source library is mounted. It is disabled when the source is missing. Adopting an already populated drive is a separate choice and never overwrites that drive with a copy.

The preview names the drive and shows the complete file count, transfer size and free space. The destination must fit the entire library plus 1 GiB; nothing is formatted or erased, and partial collections are never silently omitted. A nonempty drive is refused unless it contains this transfer tool's own resumable preparation marker. Adopting an unrelated populated Ark drive requires a separate public-configuration review; it is not an automatic merge.

Choose **Copy and verify**. The updater and library writers are excluded by the shared worker locks. The API and Kiwix reader pause while every file is copied and checked with SHA-256. The progress page reconnects when the API returns; reloading the page never requires a password by itself. If interrupted, the system-card image remains selected, partial destination files remain, and a new preview can restart the verified copy without deleting source content.

After verification, choose **Use this drive**. The tool checks the copy again, pauses writers, replaces only the library mount entry with the destination UUID, and mounts the external drive. A failed handover restores the previous mount entry, site settings and system-card mount. The external mount uses `nofail` so an absent drive does not force Linux into emergency mode. It does not silently substitute an old library if the external drive is missing.

The source image is retained at `/var/lib/dataark/demo-library.ext4`; it is not deleted or shrunk. The existing library configuration, sample registrations, readers and URLs remain in use, with an external-drive label. No redownload is required. The drive must remain connected while in use. Reclaiming system-card space is a separate maintenance step, not part of the handover. Transition requests and completion/failure enter the collection event feed used by Home Assistant.

The installer is `deploy/install_external_library.py`; it installs a fixed root-owned helper and two fixed worker services. Web requests supply only a reviewed plan ID and a discovered drive UUID, never a command or arbitrary path.

### Handover acceptance

Fourteen focused tests cover verified copying, source changes, disconnects, checksum failures, invalid UUIDs, system-drive exclusion, occupied destinations, insufficient space and mount-entry preservation. An isolated physical-Pi test using disposable ext4 images also verified a successful handover, persistence of the selected mount, retention of the source image, and automatic rollback after an injected mount failure. This test does not format or alter production drives. The removable-drive user walkthrough remains part of physical acceptance.

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

## Other storage and handover layouts

[Make another Ark](../10-User/MakeAnotherArk.md) also covers adoption of a populated drive, recovery when the configured drive is missing, generalized recipient preparation for external-library and LAN hosts, and the ready-card preparation package. The storage handover backs up public configuration and the mount entry under `/etc/dataark/storage`; its boot recovery service restores an interrupted activation. These private rollback files are not public library content. The card writer never runs from a browser request; the browser builds a package, and a local writer requires explicit disk selection and erase confirmation.

## Test record

On the physical test card, the system-card library was grown from 4 to 80 GiB. An isolated real ext4 image was first grown from 2 to 3 GiB and its sentinel hash remained unchanged. A physical reboot into recipient setup passed: the machine ID, hostname, Ark identity and SSH host keys were replaced; the provisioner key was removed. Browser API setup rejected five wrong pairing codes, enforced the cooldown, accepted the correct code afterward, and rejected reuse. The chosen admin password worked over SSH, the old SSH key was rejected, and root remained locked with direct root SSH disabled. No systemd units failed. The API was exercised from the desktop over the LAN; a phone connected through the hotspot is a separate client check. A real pseudo-terminal test confirmed that a waiting local password prompt closes when browser enrollment completes.
