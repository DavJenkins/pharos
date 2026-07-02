from fastapi import FastAPI

from app.services.status_service import get_status

app = FastAPI(
    title="Data Ark API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "application": "Data Ark",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/status")
def status():
    return get_status()
