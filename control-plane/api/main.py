"""
Aegis.net Control Plane — Main Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from api.routers import domains, health, attack_mode
from api.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("aegis_control_plane_starting", version="1.0.0")
    yield
    # Shutdown
    logger.info("aegis_control_plane_shutting_down")


app = FastAPI(
    title="Aegis.net Control Plane",
    description="API for managing Anti-DDoS protection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(domains.router, prefix="/api/v1/domains", tags=["Domains"])
app.include_router(attack_mode.router, prefix="/api/v1/attack-mode", tags=["Attack Mode"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Aegis.net Control Plane",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


