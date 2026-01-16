"""
Aegis.net — Domains Router
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
import uuid

from api.models import (
    DomainCreate, 
    DomainConfig, 
    DomainResponse, 
    DomainListResponse,
    TrafficStats,
    APIResponse
)

router = APIRouter()

# In-memory storage for MVP (replace with database later)
domains_db: dict = {}


@router.post("", response_model=DomainResponse, status_code=201)
async def create_domain(domain_data: DomainCreate):
    """
    Register a new domain for protection.
    
    Creates a new domain entry with default protection settings.
    """
    if domain_data.domain in domains_db:
        raise HTTPException(
            status_code=409,
            detail=f"Domain {domain_data.domain} already registered"
        )
    
    now = datetime.utcnow()
    domain = DomainResponse(
        id=int(now.timestamp()),
        domain=domain_data.domain,
        origin=domain_data.origin,
        protection_level=domain_data.protection_level,
        config=DomainConfig(domain=domain_data.domain, origin=domain_data.origin),
        status="active",
        created_at=now,
        updated_at=now
    )
    
    domains_db[domain_data.domain] = domain
    
    # Configure Nginx
    try:
        from api.services.nginx_manager import NginxManager
        NginxManager.create_config(
            domain=domain_data.domain,
            origin_ip=domain_data.origin,
            origin_port=80
        )
        NginxManager.reload_nginx()
    except Exception as e:
        # Re-raise exception to alert the user/CLI
        print(f"Error configuring Nginx: {e}")
        # Clean up database entry if config failed
        if domain_data.domain in domains_db:
            del domains_db[domain_data.domain]
            
        raise HTTPException(
            status_code=500,
            detail=f"Failed to configure protection: {str(e)}"
        )
    
    return domain


@router.get("", response_model=DomainListResponse)
async def list_domains(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100)
):
    """
    List all registered domains with pagination.
    """
    all_domains = list(domains_db.values())
    total = len(all_domains)
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_domains[start:end]
    
    return DomainListResponse(
        domains=paginated,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{domain}", response_model=DomainResponse)
async def get_domain(domain: str):
    """
    Get domain details and current configuration.
    """
    domain = domain.lower()
    if domain not in domains_db:
        raise HTTPException(
            status_code=404,
            detail=f"Domain {domain} not found"
        )
    
    return domains_db[domain]


@router.put("/{domain}/config", response_model=DomainResponse)
async def update_domain_config(domain: str, config: DomainConfig):
    """
    Update domain protection configuration.
    
    Changes are propagated to all edge nodes immediately.
    """
    domain = domain.lower()
    if domain not in domains_db:
        raise HTTPException(
            status_code=404,
            detail=f"Domain {domain} not found"
        )
    
    domain_obj = domains_db[domain]
    domain_obj.config = config
    domain_obj.updated_at = datetime.utcnow()
    
    # TODO: Push config to edge nodes via ConfigPusher
    
    return domain_obj


@router.delete("/{domain}", response_model=APIResponse)
async def delete_domain(domain: str):
    """
    Remove domain from protection.
    """
    domain = domain.lower()
    if domain not in domains_db:
        raise HTTPException(
            status_code=404,
            detail=f"Domain {domain} not found"
        )
    
    del domains_db[domain]
    
    return APIResponse(
        success=True,
        message=f"Domain {domain} deleted successfully"
    )


@router.get("/{domain}/stats", response_model=TrafficStats)
async def get_domain_stats(domain: str):
    """
    Get real-time traffic statistics for a domain.
    """
    domain = domain.lower()
    if domain not in domains_db:
        raise HTTPException(
            status_code=404,
            detail=f"Domain {domain} not found"
        )
    
    # Mock stats for MVP
    return TrafficStats(
        domain=domain,
        timestamp=datetime.utcnow(),
        requests_per_second=1250.5,
        legitimate_requests=12450,
        challenged_requests=2100,
        blocked_requests=1450,
        unique_ips=3420,
        top_countries={"RU": 4500, "DE": 2100, "US": 1800, "NL": 1200},
        threat_level=0.35
    )
