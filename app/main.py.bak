from fastapi import FastAPI

from app.services.status_service import get_status
from app.core.debugit import execute
from app.api.debug import router as debug_router

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
@execute("status")
def status():
    return get_status()


app.include_router(debug_router)
