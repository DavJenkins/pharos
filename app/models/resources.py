from pydantic import BaseModel


class CPU(BaseModel):
    temperature_c: float | None
    load: list[float]


class Memory(BaseModel):
    used: str
    available: str
    swap_used: str


class Disk(BaseModel):
    used: str
    free: str
    percent: int | None


class Storage(BaseModel):
    sd: Disk
    ssd: Disk


class Resources(BaseModel):
    cpu: CPU
    memory: Memory
    storage: Storage
