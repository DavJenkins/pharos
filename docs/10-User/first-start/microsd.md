# First start: Prepared microSD card

[Choose a different distribution path](../FirstStart.md) · [Download printable guide](../assets/data-ark-first-start-microsd.pdf)

A prepared card turns a compatible Raspberry Pi into a local library. It can serve its installed content without internet access. The supplied card determines the installed selection and capacity.

## What you need

- A compatible Raspberry Pi, power supply and cooling. The tested reference is a Pi 4 Model B with 2 GB RAM.
- A phone, tablet or computer with a browser. The built-in Wi-Fi is sufficient; an external USB radio is optional.

## First start

1. With the Pi powered off, insert the supplied microSD card and connect power.
2. Join the DataArk hotspot. If your device reports no internet, choose to stay connected.
3. Open http://192.168.4.1/setup.html and enter the private setup code supplied with this card.
4. Choose separate caretaker and Linux admin passwords. Allow the first startup a few minutes.

## Setup authorization

Use the private four-digit code supplied for this particular card or appliance when browser first-owner setup is pending. The supplied-card sheet and public guide use the same template; the public copy never includes a real code. Local setup can establish credentials without a code.

No online activation, DEJ Software account or registration is required. A new recipient gets a fresh identity and code rather than inheriting the original owner’s credentials.

## Hardware and operating notes

- Tested reference: Raspberry Pi 4 Model B, 2 GB RAM; CanaKit 3.5 A USB-C power supply; ventilated MazerPi case with fan and heatsinks.
- A Pi 4 with 4 GB or 8 GB RAM provides more headroom. Use a reliable supply and cooling.
- Optional range: a Linux-supported USB Wi-Fi adapter with external antenna and access-point support. Assign it to the hotspot under Wi-Fi or Hotspot / Wi-Fi adapter assignment; plugging it in alone does not change roles.
- Optional storage: add an external USB content drive using System / Library / Use an external library drive. Existing content can be copied and verified before switching. Use adequate peripheral power.

## Further help

- [Installation and bootstrap](../../30-Developer/StockPiSetup.md)
- [Container deployment](../../20-Administration/Container.md)
- [First-owner setup security](../../20-Administration/SetupSecurity.md)
