"""
Rate Limiting Configuration Models
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime


class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a domain"""
    
    domain: str = Field(..., description="Domain name")
    
    # Global limits
    requests_per_second: Optional[int] = Field(None, ge=1, description="Global RPS limit")
    requests_per_minute: Optional[int] = Field(None, ge=1, description="Global RPM limit")
    
    # Per-IP limits
    per_ip_rps: Optional[int] = Field(None, ge=1, description="Per-IP RPS limit")
    per_ip_rpm: Optional[int] = Field(None, ge=1, description="Per-IP RPM limit")
    
    # Burst settings
    burst_allowance: int = Field(10, ge=0, description="Burst size allowance")
    
    # IP lists
    whitelist_ips: List[str] = Field(default_factory=list, description="IPs without limits")
    blacklist_ips: List[str] = Field(default_factory=list, description="Blocked IPs")
    
    # Geographic limits
    country_limits: Dict[str, int] = Field(default_factory=dict, description="Per-country RPS limits")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(True, description="Whether rate limiting is active")
    
    @validator('requests_per_second', 'requests_per_minute', 'per_ip_rps', 'per_ip_rpm')
    def validate_limits(cls, v):
        """Ensure limits are reasonable for 4GB RAM constraint"""
        if v is not None and v > 1_000_000:
            raise ValueError("Limit too high for available resources (max 1M)")
        return v
    
    @validator('whitelist_ips', 'blacklist_ips')
    def validate_ip_lists(cls, v):
        """Limit IP list sizes to conserve memory"""
        if len(v) > 10_000:
            raise ValueError("IP list too large (max 10,000 entries)")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "requests_per_second": 1000,
                "requests_per_minute": 50000,
                "per_ip_rps": 10,
                "per_ip_rpm": 500,
                "burst_allowance": 20,
                "whitelist_ips": ["1.2.3.4"],
                "blacklist_ips": ["5.6.7.8"],
                "country_limits": {"CN": 100, "RU": 100}
            }
        }


class RateLimitStats(BaseModel):
    """Rate limiting statistics"""
    
    domain: str
    total_requests: int = 0
    blocked_requests: int = 0
    current_rps: float = 0.0
    unique_ips: int = 0
    top_ips: List[Dict[str, any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class RateLimitConfigCreate(BaseModel):
    """Request model for creating rate limit config"""
    
    domain: str
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    per_ip_rps: Optional[int] = None
    per_ip_rpm: Optional[int] = None
    burst_allowance: int = 10
    whitelist_ips: List[str] = Field(default_factory=list)
    blacklist_ips: List[str] = Field(default_factory=list)
    country_limits: Dict[str, int] = Field(default_factory=dict)


class RateLimitConfigUpdate(BaseModel):
    """Request model for updating rate limit config"""
    
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    per_ip_rps: Optional[int] = None
    per_ip_rpm: Optional[int] = None
    burst_allowance: Optional[int] = None
    whitelist_ips: Optional[List[str]] = None
    blacklist_ips: Optional[List[str]] = None
    country_limits: Optional[Dict[str, int]] = None
    active: Optional[bool] = None
