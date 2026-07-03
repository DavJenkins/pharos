from pydantic import BaseModel, Field


class Signal(BaseModel):
    dbm: int | None = Field(
        None,
        description="Received signal strength (dBm)"
    )

    percent: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Signal quality percentage"
    )


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


class CPU(BaseModel):
    temperature_c: float
    load: list[float]


class Memory(BaseModel):
    used: str
    available: str
    swap_used: str


class Disk(BaseModel):
    used: str
    free: str
    percent: int


class Storage(BaseModel):
    sd: Disk
    ssd: Disk


class Resources(BaseModel):
    cpu: CPU
    memory: Memory
    storage: Storage


class System(BaseModel):
    hostname: str
    platform: str
    uptime: str


class Services(BaseModel):
    fastapi: str = "running"


class Status(BaseModel):
    state: str
    debug: bool
    sync: str = "Idle"
    updated: str | None = None


class StatusResponse(BaseModel):
    network: Network
    system: System
    resources: Resources
    services: Services
    status: Status
