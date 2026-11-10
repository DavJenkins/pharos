# First start: Linux LAN server

[Choose a different distribution path](../FirstStart.md) · [Download printable guide](../assets/data-ark-first-start-linux-lan.pdf)

A Data Ark can serve an existing local network from a supported Linux server or laptop. A Wi-Fi access point is optional, and a Pi is not required for this profile.

## What you need

- A supported Debian-based host, administrative access and an existing wired or Wi-Fi network.
- Library storage and internet for installation dependencies.

## First start

1. Use the supported bootstrap workflow and select the LAN profile. Preserve the host's existing network configuration.
2. Choose a library location or attach an existing content drive. Set the caretaker password through the trusted local installer.
3. Open the host's LAN address in a browser and check the dashboard, Help and installed readers.
4. Use the host's existing Linux account credentials for SSH. There is no extra activation code after owner credentials have been established.

## Setup authorization

Set credentials through the trusted local installer or Docker host terminal. No separate activation code is required afterward. If browser setup is deliberately deferred over a shared network, recipient preparation supplies a new private pairing code.

No online activation, DEJ Software account or registration is required. A new recipient gets a fresh identity and code rather than inheriting the original owner’s credentials.

## Hardware and operating notes

- A LAN server does not need a hotspot, a second Wi-Fi adapter or Raspberry Pi-specific hardware.
- If ownership is handed to someone else with browser setup deferred, generate a fresh private pairing code through recipient preparation.

## Further help

- [Installation and bootstrap](../../30-Developer/StockPiSetup.md)
- [Container deployment](../../20-Administration/Container.md)
- [First-owner setup security](../../20-Administration/SetupSecurity.md)
