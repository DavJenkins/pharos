from pydantic import BaseModel, Field

from app.models.network import Network
from app.models.resources import Resources
from app.models.services import Services
from app.models.system import System


class Status(BaseModel):
    state: str
    debug: bool
    sync: str = "Unavailable"
    update: dict | None = None
    issues: list[str] = Field(default_factory=list)
    updated: str | None = None


class StatusResponse(BaseModel):
    network: Network | None
    system: System | None
    resources: Resources | None
    services: Services
    status: Status
