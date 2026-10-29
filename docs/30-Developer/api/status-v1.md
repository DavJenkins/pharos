# Data Ark REST API

## Endpoint

GET /api/status

Returns the current operating status of the Data Ark appliance.

---

# Top Level Objects

| Object | Purpose |
|---------|---------|
| network | Network interfaces and connectivity |
| system | Operating system and hardware information |
| resources | CPU, memory and storage |
| services | Health of Data Ark services |
| status | Overall appliance state |

---

# network

## ethernet

| Field | Type | Description |
|------|------|-------------|
| state | string | up/down |
| connected | boolean | Link available |
| ip | string | IPv4 address |
| gateway | string | Default gateway |

## wifi

| Field | Type | Description |
|------|------|-------------|
| state | string | connected/disconnected |
| connected | boolean | Connected to AP |
| ssid | string/null | Connected SSID |
| signal.dbm | integer/null | RSSI |
| signal.percent | integer/null | Signal quality |
| rate | string | PHY rate |
| ip | string | IPv4 address |
| gateway | string | Default gateway |

## access_point

| Field | Type | Description |
|------|------|-------------|
| ssid | string | AP SSID |
| client_count | integer | Number of clients |
| clients | array | Connected clients |

---

# system

| Field | Type | Description |
|------|------|-------------|
| hostname | string | Linux hostname |
| platform | string | Hardware model |
| uptime | string | Human readable uptime |

---

# resources

## cpu

| Field | Type |
|------|------|
| temperature_c | number |
| load | array[3] |

## memory

| Field | Type |
|------|------|
| used_bytes | integer |
| available_bytes | integer |
| swap_used_bytes | integer |
| used | string |
| available | string |
| swap_used | string |

## storage.sd

| Field | Type |
|------|------|
| used | string |
| free | string |
| percent | integer |

## storage.ssd

| Field | Type |
|------|------|
| used | string |
| free | string |
| percent | integer |

---

# services

Example

{
    "fastapi":"running",
    "apache":"running",
    "hostapd":"running",
    "dnsmasq":"running",
    "kiwix":"running",
    "samba":"running"
}

---

# status

| Field | Type | Description |
|------|------|-------------|
| state | string | ok, degraded, error |
| debug | boolean | Debug mode enabled |
| sync | string | Synchronization state |
| updated | string | ISO-8601 timestamp |

---

# Compatibility Policy

Version: 1

Rules

* Existing fields SHALL NOT be renamed within Version 1.
* Existing fields SHALL NOT change type within Version 1.
* New fields MAY be added.
* Clients MUST ignore fields they do not recognize.
* Missing optional values SHALL be represented as null.



## Telemetry failure semantics

`network`, `system`, and `resources` may be null when their collector fails.
`temperature_c` and disk `percent` may be null when readings are unavailable.
Clients must handle these values rather than treating them as zero.
`status.issues` contains explanations for degraded or error state.
`status.updated` is a UTC timestamp with an explicit offset.
`status.sync` is rsync process activity: Syncing, Idle, or Unavailable.
The current service probes expose fastapi, apache, network_manager, samba, and kiwix;
the example service list above is illustrative, not a set of implemented probes.


## Simultaneous network interfaces

Ethernet (eth0), the assigned upstream Wi-Fi radio, and the assigned hotspot radio are
independent. Multiple interfaces may be active together. These fields do not
select a preferred route or establish internet reachability.

Ethernet and Wi-Fi connected values are null when the collector cannot establish
state. Access-point active is true when iw reports AP mode and NetworkManager
reports that the assigned hotspot interface is connected, false when known inactive, and null when unknown.
The AP also exposes state and ip. Client count is separate: an active AP with
zero clients remains active in the dashboard.
