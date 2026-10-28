# Wi-Fi adapter assignment

The hotspot is the Ark's essential wireless service. Either access-point-capable
radio can serve it; the other radio provides optional upstream internet access.
The built-in Pi radio and Netgear A6150 USB radio are separate adapters.
Driver-reported AP support is checked before accepting a choice; dependable
coverage still needs a real client test.

Open **Settings → Hotspot → Access point settings → Wi-Fi adapter assignment**,
or use `/config/adapters.html`. The same link is on the upstream Wi-Fi page.
Choose **Load adapters** and enter the caretaker password in the on-demand pop-up, then select the hotspot radio and apply. The password pop-up offers a slide switch to remember it for 1–120 minutes (default 10) across pages in the same browser tab and Ark address. Both the Wi-Fi and Hotspot status pop-ups also link directly to adapter assignment.
Clients disconnect briefly. Reconnect to DataArk, return to this page, load
adapters and choose **Keep this assignment** within four minutes. Ethernet is
unaffected. Without confirmation, an independent system timer restores the
previous assignment. Activation failures trigger immediate restoration.

Saved SSIDs and passwords remain in NetworkManager. Adapter switching moves
interface bindings; it does not delete those network profiles. Internet
pass-through resets to off. Portal DNS, forwarding policy, diagnostics, access
path protection, status and connected-device collection follow the new roles.
Other network changes are blocked until a pending assignment is resolved.

## Configuration and recovery

* `/etc/dataark/wifi-roles.json`: human-readable preferred hotspot permanent MAC
  address and built-in fallback policy. No passwords. Interface names are not
  used as the persistent hardware identity.
* `/run/dataark-wifi-roles.json`: actual hotspot/upstream interfaces for this boot.
* `/var/lib/dataark/wifi-roles/pending.json`: root-only rollback snapshot and
  confirmation deadline; no Wi-Fi passwords are copied into it.
* `dataark-wifi-roles.service`: startup reconciliation. If the preferred USB
  adapter is absent, the built-in AP-capable radio takes over. The preference is
  retained for the next startup. USB removal while running is not automatic
  failover; reconnect the adapter or use Ethernet/local console and restart.
* `dataark-wifi-rollback.timer`: independent four-minute rollback after a change.
  A reboot with an unconfirmed change restores the prior assignment first.

`deploy/install_network_admin.py` installs the fixed-scope role manager and reader
via `deploy/install_wifi_roles.py`. Installation retains the current assignment.
No additional general-purpose sudo permission is added.

Recovery-kit preparation mirrors the public preference to
`/mnt/storage/DATA-ARK-RECOVERY/wifi-roles.json`. Stock-Pi setup starts with the
documented built-in hotspot, then imports the preference and reconciles it with
the adapters actually present. A clone with different adapter hardware falls
back to its built-in radio; select its USB radio on the new device if wanted.
Confirmed choices also refresh the preference in the mounted recovery kit. Spare-media
acceptance remains required before treating the wider recovery path as dependable.

For a local-console recovery, use
`sudo /usr/local/libexec/dataark-wifi-roles --rollback` for a pending change, or
`sudo systemctl restart dataark-wifi-roles` to reconcile the saved preference.
Keep a wired connection or the Pi's local keyboard/display available when testing
a new radio assignment. Do not use `nmcli radio wifi off`: it disables both radios.
