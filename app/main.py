from fastapi import FastAPI

from app.routers.about import router as about_router
from app.routers.debug import router as debug_router
from app.routers.events import router as events_router
from app.routers.network import router as network_router
from app.routers.network_admin import router as network_admin_router
from app.routers.status import router as status_router

app = FastAPI(
    title="Data Ark API",
    version="1.0.0",
    description="REST API for the Data Ark appliance",
    root_path="/api",
)

app.include_router(about_router)
app.include_router(status_router)
app.include_router(network_router)
app.include_router(network_admin_router)
app.include_router(events_router)
app.include_router(debug_router)


@app.get("/")
def root():
    return {
        "application": "Data Ark",
        "version": app.version,
        "status": "running",
    }
