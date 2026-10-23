# Data Ark (Project Pharos)

> **Data Ark is an appliance for preserving civilization's practical knowledge.**

Start with the [complete handbook and handover](docs/00-Introduction/Handbook.md), [deployed configuration reference](docs/20-Administration/Configuration.md), and [image-to-Ark bootstrap plan](docs/30-Developer/BootstrapPlan.md). The local working source is `/opt/dataark` on the Ark and the `\\dataark\dataark` development share; the canonical remote is [DavJenkins/pharos](https://github.com/DavJenkins/pharos).


![Pharos Data Ark](app/static/assets/Pharos%20Data%20Ark.png)

---

## Why Data Ark?

When everything is working normally, the Internet feels permanent.

It isn't.

Storms, wildfires, hurricanes, earthquakes, power failures, cyberattacks, infrastructure damage, and simple service outages can all make critical information inaccessible exactly when it is needed most.

Data Ark was created from a simple idea:

> **Essential knowledge should remain available, even when the Internet does not.**

The Ark's primary purpose is to preserve and serve useful content under adverse conditions. In those conditions, the network, Linux computer, storage, terminal and tools it brings along are also potential peripheral resources. Make those capabilities discoverable and useful while protecting the library's availability. See [Resources beyond the library](docs/10-User/Resources.md).


Rather than depending on cloud services or continuous connectivity, Data Ark packages a carefully curated collection of information into a self-contained appliance built around inexpensive, low-power hardware.

Anyone nearby can connect with a phone, tablet, or laptop and immediately access practical knowledge without creating an account, installing software, or connecting to the Internet.

Whether repairing a generator, diagnosing an equipment failure, identifying a medical condition, rebuilding after a storm, locating emergency resources, or simply looking up how something works, the information remains available.

---

# What is Data Ark?

Data Ark is an offline-first digital knowledge appliance built around the Raspberry Pi.

Unlike a traditional NAS, file server, or web server, Data Ark is designed to behave like an appliance:

- Power it on.
- Connect to its Wi-Fi.
- Start using it.

The system combines curated offline resources with an intuitive web interface and a documented REST API to provide a portable, resilient library that continues functioning when normal communication infrastructure does not.

Its design emphasizes:

- Offline operation
- Simplicity
- Reliability
- Low power consumption
- Long-term maintainability
- Open architecture
- Ease of administration

---

# Vision

Imagine walking into a shelter after a hurricane.

The electrical grid is unstable.

Cell towers are offline.

Internet access is unavailable.

Yet anyone can connect to a Wi-Fi network called **DataArk** and immediately access:

- Wikipedia
- WikiMed
- Project Gutenberg
- OpenStreetMap
- Government emergency information
- Local building codes
- Equipment repair manuals
- Household documentation
- Family emergency information
- Medical references
- Amateur radio resources
- Survival manuals
- Any additional resources curated by the owner

No cloud.

No subscriptions.

No Internet required.

---

# Design Philosophy

## Offline First

Everything important should work without Internet access.

Internet connectivity is treated as an enhancement—not a requirement.

---

## Appliance, Not Server

Users should not need Linux knowledge or system administration experience.

The system should feel like using an appliance rather than administering a computer.

---

## Preserve Knowledge

Technology changes.

Companies disappear.

Websites vanish.

Knowledge should not disappear simply because an online service became unavailable.

---

## Open and Extensible

Every component should be understandable.

Every subsystem should be documented.

Every part should be replaceable.

Future owners should be able to maintain and improve the system without depending on proprietary services.

---

# Current Features

## Dashboard

- Responsive appliance-style web interface
- Live system status indicators
- Mobile-friendly design
- Configurable automatic refresh
- Debug mode
- REST API integration

---

## Knowledge Libraries

Current integrations include:

- Wikipedia
- WikiMed
- Project Gutenberg
- OpenStreetMap
- Raspberry Pi documentation
- U.S. Government resources

The architecture is designed to make additional offline libraries easy to integrate.

---

## REST API

FastAPI provides a documented REST API for:

- System status
- Health monitoring
- Administration
- Future automation

Swagger documentation is available at:

```
http://dataark/api/docs
```

---

## Documentation

Documentation is generated and deployed with the application.

Current manuals include:

- Introduction
- User Guide
- Administrator Guide
- Developer Guide
- API Documentation
- Architecture Notes
- Release Notes

---

## Wi-Fi Appliance Mode

Data Ark can operate as its own wireless access point.

Users simply connect to:

```
SSID: DataArk
```

and are presented with the local portal.

Internet connectivity is optional.

---

## Deployment

A single deployment script publishes:

- Static website
- Documentation
- Static assets

```
deploy/deploy-web.sh
```

The website itself is maintained under source control and deployed automatically rather than edited directly on the running system.

---

# Architecture

```
                     Internet (Optional)
                            │
                    Wi-Fi Client (wlan1)
                            │
                  ┌─────────────────────┐
                  │     Raspberry Pi    │
                  │                     │
                  │     FastAPI API     │
                  │     Apache          │
                  │     Documentation   │
                  │     Offline Library │
                  │                     │
                  └──────────┬──────────┘
                             │
                     Wi-Fi AP (wlan0)
                      SSID: DataArk
                             │
          Phones • Tablets • Laptops • Desktops
```

---

# Repository Layout

```
app/
    static/
        assets/
        css/
        js/
        config/
        index.html

deploy/
    deploy-web.sh

docs/
    Project documentation

tools/
    Utility scripts

legacy/
    Historical code and experiments
```

---

# Development

Clone the repository:

```bash
git clone https://github.com/DavJenkins/pharos.git
```

Deploy the website:

```bash
./deploy/deploy-web.sh
```

The deployment script publishes:

- Static website
- Documentation
- Assets

to the running appliance.

---

# Roadmap

## Dashboard

- [ ] Configurable dashboard widgets
- [ ] Theme support
- [ ] Better mobile experience
- [ ] System graphs
- [ ] Notification center

---

## Knowledge

- [ ] CD3WD Engineering Library
- [ ] Equipment repair manuals
- [ ] FEMA publications
- [ ] Local ordinances
- [ ] Building codes
- [ ] Amateur radio references
- [ ] Survival manuals
- [ ] Medical reference expansion

---

## Appliance

- [ ] Automatic content updates
- [ ] Backup and restore
- [ ] Storage management
- [ ] User accounts
- [ ] Health monitoring
- [ ] Configuration backup

---

## Hardware

- [ ] Battery monitoring
- [ ] Solar charging integration
- [ ] Generator monitoring
- [ ] Environmental sensors
- [ ] UPS support

---

# Technology Stack

- Raspberry Pi
- Python
- FastAPI
- Apache
- JavaScript
- HTML5
- CSS
- NetworkManager
- Kiwix

---

# Project Philosophy

Data Ark is not intended to compete with the Internet.

It exists because the Internet is extraordinary—and because experience has shown that extraordinary infrastructure is not always available.

The project assumes that the most valuable information is often the information you cannot retrieve when you suddenly need it.

By preserving essential knowledge in a self-contained appliance, Data Ark seeks to make that knowledge available to anyone, anywhere, regardless of connectivity.

---

# Why "Pharos"?

More than two thousand years ago, the Lighthouse of Alexandria—known as **Pharos**—guided ships safely through uncertainty.

Its purpose was not merely to provide light, but to preserve lives by making knowledge visible when it mattered most.

Project Pharos adopts the same philosophy.

Instead of guiding ships through darkness, Data Ark preserves and illuminates practical human knowledge, making it available when ordinary communication systems fail.

The goal is not to replace the Internet.

The goal is to remain useful when the Internet cannot.

---

# Contributing

Data Ark is under active development.

Bug reports, feature suggestions, documentation improvements, and pull requests are welcome.

The long-term goal is to create an appliance that anyone can deploy, understand, maintain, and trust.

---

# License

License selection is currently under consideration.

Until a license is published, all rights are reserved by the project author.

---

# Acknowledgements

Data Ark builds upon the work of many outstanding open-source projects and organizations, including:

- Raspberry Pi Foundation
- FastAPI
- Apache HTTP Server
- Kiwix
- OpenStreetMap
- Project Gutenberg
- Wikipedia
- WikiMed
- The Python Software Foundation

Without their work, projects like Data Ark would not be possible.
