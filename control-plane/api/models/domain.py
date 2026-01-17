"""
Aegis.net — Pydantic Models (Schemas)
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import IntEnum


class ProtectionLevel(IntEnum):
    """Protection levels for Smart Shield."""
    OBSERVE = 0
    SOFT = 1
    MEDIUM = 2
    HARD = 3
    LOCKDOWN = 4


# ========================
# Domain Schemas
# ========================

class DomainBase(BaseModel):
    """Base domain schema."""
    domain: str = Field(..., min_length=3, max_length=253, examples=["example.com"])
    
    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain format."""
        v = v.lower().strip()
        if not v or ".." in v:
            raise ValueError("Invalid domain format")
        return v


class DomainCreate(DomainBase):
    """Schema for creating a new domain."""
    origin_ip: str = Field(..., examples=["192.168.1.1"])
    origin_port: int = Field(default=443, ge=1, le=65535)


class DomainConfig(BaseModel):
    """Domain protection configuration."""
    protection_level: ProtectionLevel = Field(default=ProtectionLevel.OBSERVE)
    rate_limit_per_ip: int = Field(default=100, ge=1, le=10000, description="Requests per second per IP")
    whitelist_ips: List[str] = Field(default_factory=list)
    blacklist_ips: List[str] = Field(default_factory=list)
    custom_rules: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Game-specific settings
    game_protocol: Optional[str] = Field(default=None, examples=["minecraft", "rage_mp", "source"])
    game_port: Optional[int] = Field(default=None)
    
    # Challenge settings
    challenge_type: str = Field(default="invisible_pow", examples=["invisible_pow", "captcha", "js_challenge"])
    challenge_timeout: int = Field(default=3600, description="Challenge cache duration in seconds")


class DomainResponse(DomainBase):
    """Domain response with full details."""
    id: str
    origin_ip: str
    origin_port: int
    config: DomainConfig
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """Paginated list of domains."""
    domains: List[DomainResponse]
    total: int
    page: int
    per_page: int


# ========================
# Attack Mode Schemas
# ========================

class AttackModeRequest(BaseModel):
    """Request to activate attack mode."""
    level: ProtectionLevel
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    reason: Optional[str] = Field(default=None, max_length=500)


class AttackModeResponse(BaseModel):
    """Attack mode activation response."""
    domain: str
    level: ProtectionLevel
    previous_level: ProtectionLevel
    activated_at: datetime
    expires_at: datetime
    auto_decrease: bool = True


# ========================
# Statistics Schemas
# ========================

class TrafficStats(BaseModel):
    """Real-time traffic statistics."""
    domain: str
    timestamp: datetime
    requests_per_second: float
    legitimate_requests: int
    challenged_requests: int
    blocked_requests: int
    unique_ips: int
    top_countries: Dict[str, int]
    threat_level: float = Field(ge=0, le=1)


class AttackEvent(BaseModel):
    """Attack event details."""
    id: str
    domain: str
    started_at: datetime
    ended_at: Optional[datetime]
    attack_type: str
    peak_rps: float
    total_requests_blocked: int
    source_countries: List[str]
    mitigated: bool


# ========================
# API Response Wrappers
# ========================

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
