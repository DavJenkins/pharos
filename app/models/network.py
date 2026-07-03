from pydantic import BaseModel, Field


class Signal(BaseModel):
    dbm: int | None = Field(None, description="Received signal strength (dBm)")
    percent: int | None = Field(None, ge=0, le=100)


class Ethernet(BaseModel):
    state: str
    connected: bool
    ip: str
    gateway: str


class Wifi(BaseModel):
    state: str
    connected: bool
    ssid: str | None
    signal: Signal
    rate: str | None
    ip: str
    gateway: str


class AccessPoint(BaseModel):
    ssid: str
    client_count: int
    clients: list[dict]


class Network(BaseModel):
    ethernet: Ethernet
    wifi: Wifi
    access_point: AccessPoint
