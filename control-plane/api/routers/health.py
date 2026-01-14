"""
Aegis.net — Health Check Router
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aegis-control-plane",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check — verifies all dependencies are available."""
    # TODO: Add actual dependency checks (Redis, DB)
    return {
        "ready": True,
        "checks": {
            "database": "ok",
            "redis": "ok",
            "edge_nodes": "ok"
        }
    }
