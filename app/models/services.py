from pydantic import BaseModel


class Services(BaseModel):
    fastapi: str = "running"
