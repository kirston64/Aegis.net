"""
Rate Limiting API Router - CLI-only endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
import structlog

from ..models.ratelimit_config import (
    RateLimitConfig,
    RateLimitConfigCreate,
    RateLimitConfigUpdate,
    RateLimitStats
)
from ..services.ratelimit_service import get_ratelimit_service, RateLimitService
from ..services.auth import get_auth_service, AuthService
from ..services.audit_logger import get_audit_logger, AuditLogger
from .auth import get_current_user

logger = structlog.get_logger()
router = APIRouter()


@router.post("/config", response_model=RateLimitConfig, status_code=status.HTTP_201_CREATED)
async def create_ratelimit_config(
    config_data: RateLimitConfigCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """Create or update rate limiting configuration for a domain (CLI-only)"""
    
    # Create config object
    config = RateLimitConfig(**config_data.model_dump())
    
    # Save configuration
    result = ratelimit_service.create_or_update_config(config)
    
    # Audit log
    audit_logger.log_action(
        user=current_user["sub"],
        action="ratelimit.config.create",
        details={
            "domain": config.domain,
            "rps": config.requests_per_second,
            "rpm": config.requests_per_minute
        },
        client_ip=current_user.get("client_ip")
    )
    
    return result


@router.get("/config/{domain}", response_model=RateLimitConfig)
async def get_ratelimit_config(
    domain: str,
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service)
):
    """Get rate limiting configuration for a domain"""
    
    config = ratelimit_service.get_config(domain)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit configuration not found for domain: {domain}"
        )
    
    return config


@router.get("/config", response_model=List[RateLimitConfig])
async def list_ratelimit_configs(
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service)
):
    """List all rate limiting configurations"""
    
    configs = ratelimit_service.list_configs()
    return configs


@router.put("/config/{domain}", response_model=RateLimitConfig)
async def update_ratelimit_config(
    domain: str,
    config_update: RateLimitConfigUpdate,
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """Update rate limiting configuration for a domain (CLI-only)"""
    
    # Get existing config
    existing_config = ratelimit_service.get_config(domain)
    
    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit configuration not found for domain: {domain}"
        )
    
    # Update fields
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_config, field, value)
    
    # Save updated config
    result = ratelimit_service.create_or_update_config(existing_config)
    
    # Audit log
    audit_logger.log_action(
        user=current_user["sub"],
        action="ratelimit.config.update",
        details={
            "domain": domain,
            "updated_fields": list(update_data.keys())
        },
        client_ip=current_user.get("client_ip")
    )
    
    return result


@router.delete("/config/{domain}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ratelimit_config(
    domain: str,
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """Delete rate limiting configuration for a domain (CLI-only)"""
    
    success = ratelimit_service.delete_config(domain)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit configuration not found for domain: {domain}"
        )
    
    # Audit log
    audit_logger.log_action(
        user=current_user["sub"],
        action="ratelimit.config.delete",
        details={"domain": domain},
        client_ip=current_user.get("client_ip")
    )
    
    return None


@router.get("/stats/{domain}", response_model=RateLimitStats)
async def get_ratelimit_stats(
    domain: str,
    current_user: dict = Depends(get_current_user),
    ratelimit_service: RateLimitService = Depends(get_ratelimit_service)
):
    """Get rate limiting statistics for a domain"""
    
    stats = ratelimit_service.get_stats(domain)
    return stats
