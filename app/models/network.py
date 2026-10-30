from pydantic import BaseModel, Field


class Signal(BaseModel):
    dbm: int | None = Field(None, description="Received signal strength (dBm)")
    percent: int | None = Field(None, ge=0, le=100)


class Ethernet(BaseModel):
    interface: str = 'eth0'
    permanent_mac: str | None = None
    addresses: list[str] = Field(default_factory=list)
    default_route: bool = False
    route_metric: int | None = None
    managed: bool = True
    carrier: bool | None = None
    enabled: bool | None = None
    state: str
    connected: bool | None
    ip: str
    gateway: str


class Wifi(BaseModel):
    interface: str = "wlan1"
    enabled: bool | None = None
    state: str
    connected: bool | None
    ssid: str | None
    signal: Signal
    rate: str | None
    ip: str
    gateway: str


class AccessPoint(BaseModel):
    interface: str = "wlan0"
    enabled: bool | None = None
    active: bool | None = None
    state: str = "unknown"
    ip: str = ""
    ssid: str
    client_count: int
    clients: list[dict]


class Network(BaseModel):
    capabilities: dict = Field(default_factory=dict)
    ethernet: Ethernet
    ethernet_interfaces: list[Ethernet] = Field(default_factory=list)
    wifi: Wifi
    access_point: AccessPoint
