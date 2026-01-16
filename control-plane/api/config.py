"""
Aegis.net Control Plane — Configuration
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Aegis.net Control Plane"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aegis"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://aegis.net"]
    
    # Edge nodes
    EDGE_NODES: List[str] = [
        "https://fra1.edge.aegis.net",
        "https://ams1.edge.aegis.net",
        "https://mow1.edge.aegis.net",
    ]
    
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    
    # CLI Security
    CLI_SESSION_TIMEOUT: int = 1800  # 30 minutes
    JWT_SECRET: str = "change-this-to-random-secret-in-production"  # For CLI session tokens
    
    # Authorized SSH public keys for CLI access
    AUTHORIZED_CLI_KEYS: List[str] = [
        # Add your SSH public keys here
        # Example: "ssh-ed25519 AAAAC3... user@host"
    ]
    
    # IP whitelist for CLI access (empty list = allow all)
    WHITELISTED_IPS: List[str] = [
        "127.0.0.1",
        "::1",
        # Add your trusted IPs here
    ]
    
    # Audit logging
    AUDIT_LOG_RETENTION_DAYS: int = 90
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
