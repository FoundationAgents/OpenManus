"""
OpenManus Backend Main Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.manus import router as manus_router
from backend.app.api.routes.workspace import router as workspace_router
from backend.app.core.config import config

# Create FastAPI application
app = FastAPI(
    title="OpenManus Backend API",
    description="HTTP API for OpenManus agent",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(manus_router)
app.include_router(workspace_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    from backend.app.events import initialize_event_handlers

    initialize_event_handlers()
