from fastapi import FastAPI

from app.models.status import StatusResponse
from app.services.status_service import get_status

app = FastAPI(
    title="Data Ark API",
    version="1.0.0",
    description="REST API for the Data Ark appliance",
)


@app.get("/")
def root():
    return {
        "application": "Data Ark",
        "version": "1.0.0",
        "status": "running",
    }


@app.get(
    "/status",
    response_model=StatusResponse,
    summary="Current appliance status",
    tags=["Status"],
)
def status():
    return get_status()
