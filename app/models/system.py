from pydantic import BaseModel


class System(BaseModel):
    hostname: str
    platform: str
    uptime: str
