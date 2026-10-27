from fastapi import FastAPI

from app.routers.about import router as about_router
from app.routers.debug import router as debug_router
from app.routers.events import router as events_router
from app.routers.network import router as network_router
from app.routers.network_admin import router as network_admin_router
from app.routers.status import router as status_router
from app.routers.portal import router as portal_router

app = FastAPI(
    title="Data Ark API",
    version="1.0.0",
    description="REST API for the Data Ark appliance",
    root_path="/api",
    docs_url=None,
    redoc_url=None,
)

from app.routers.documentation import router as documentation_router
app.include_router(documentation_router)
from app.routers.https_setup import router as https_setup_router
app.include_router(https_setup_router)

from app.routers.bugout import router as bugout_router
app.include_router(bugout_router)

app.include_router(about_router)
app.include_router(status_router)
app.include_router(portal_router)
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

from app.routers.library import router as library_router
app.include_router(library_router)

from app.routers.callsigns import router as callsigns_router
app.include_router(callsigns_router)

from app.routers.community import router as community_router
app.include_router(community_router)

from app.routers.source_check import router as source_check_router
app.include_router(source_check_router)

from app.routers.integration_health import router as integration_health_router
app.include_router(integration_health_router)

from app.routers.recovery import router as recovery_router
app.include_router(recovery_router)
