"""
Aegis.net Control Plane — Main Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import redis

from api.routers import domains, health, attack_mode, ratelimit, auth as auth_router, audit
from api.config import settings
from api.services.auth import init_auth_service
from api.services.ratelimit_service import init_ratelimit_service
from api.services.audit_logger import init_audit_logger

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
    
    # Initialize Redis connection
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("redis_connected", url=settings.REDIS_URL)
    
    # Initialize security services
    init_auth_service(
        authorized_keys=settings.AUTHORIZED_CLI_KEYS,
        whitelisted_ips=settings.WHITELISTED_IPS,
        jwt_secret=settings.JWT_SECRET,
        session_timeout=settings.CLI_SESSION_TIMEOUT
    )
    
    init_ratelimit_service(redis_client)
    init_audit_logger(redis_client, settings.AUDIT_LOG_RETENTION_DAYS)
    
    logger.info("security_services_initialized")
    
    yield
    
    # Shutdown
    redis_client.close()
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
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(domains.router, prefix="/api/v1/domains", tags=["Domains"])
app.include_router(attack_mode.router, prefix="/api/v1/attack-mode", tags=["Attack Mode"])
app.include_router(ratelimit.router, prefix="/api/v1/ratelimit", tags=["Rate Limiting"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Aegis.net Control Plane",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


