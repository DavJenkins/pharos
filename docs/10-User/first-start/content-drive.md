# First start: Content drive / split Ark

[Choose a different distribution path](../FirstStart.md) · [Download printable guide](../assets/data-ark-first-start-content-drive.pdf)

A library drive carries public content, configuration and the recovery kit. It can help rebuild a replacement host. A surviving host can prepare replacement library media. A content drive alone is not a bootable operating system.

## What you need

- A supported running Linux host with administrative access and an attached library drive.
- Internet for missing operating-system packages and software dependencies. Existing public content is reused.

## First start

1. Attach the library drive. Locate its DATA-ARK-CONFIG folder and included recovery kit; follow its README rather than executing an arbitrary script from unknown media.
2. Preview the bootstrap/recovery plan on the new host and select the intended library location.
3. Run the supported installation workflow with Linux administrative authorization. Set owner credentials locally when offered.
4. Verify library readers and content. When preparing a second Ark for someone else, use Make another Ark / Prepare for a new owner to establish a fresh identity and private setup code.

## Setup authorization

Set credentials through the trusted local installer or Docker host terminal. No separate activation code is required afterward. If browser setup is deliberately deferred over a shared network, recipient preparation supplies a new private pairing code.

No online activation, DEJ Software account or registration is required. A new recipient gets a fresh identity and code rather than inheriting the original owner’s credentials.

## Hardware and operating notes

- Never reuse the original owner credentials or printed setup code for a new recipient.
- When starting with configuration but no content, choose a capacity-appropriate restore preset; downloads need an upstream connection.

## Further help

- [Installation and bootstrap](../../30-Developer/StockPiSetup.md)
- [Container deployment](../../20-Administration/Container.md)
- [First-owner setup security](../../20-Administration/SetupSecurity.md)
