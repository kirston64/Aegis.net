"""
Audit Log API Router
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
import structlog

from ..services.audit_logger import get_audit_logger, AuditLogger
from .auth import get_current_user

logger = structlog.get_logger()
router = APIRouter()


@router.get("/log")
async def get_audit_log(
    limit: int = Query(100, ge=1, le=1000, description="Number of log entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: Optional[str] = Query(None, description="Filter by user"),
    action: Optional[str] = Query(None, description="Filter by action"),
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get audit log entries
    
    Returns recent audit log entries with optional filtering.
    Requires CLI authentication.
    """
    
    if user or action:
        logs = audit_logger.search_logs(user=user, action=action, limit=limit)
    else:
        logs = audit_logger.get_logs(limit=limit, offset=offset)
    
    return {"logs": logs, "count": len(logs)}
