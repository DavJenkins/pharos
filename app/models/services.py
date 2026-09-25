from pydantic import BaseModel


class Services(BaseModel):
    fastapi: str = "running"
    apache: str = "unknown"
    network_manager: str = "unknown"
    samba: str = "unknown"
    kiwix: str = "unknown"
