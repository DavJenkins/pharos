from pydantic import BaseModel

from app.models.network import Network
from app.models.resources import Resources
from app.models.services import Services
from app.models.system import System


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
