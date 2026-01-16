"""
CLI Configuration and Security Settings
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class CLISettings(BaseSettings):
    """CLI application settings"""
    
    # Connection settings
    DEFAULT_PORT: int = 8000
    SESSION_TIMEOUT_SECONDS: int = 1800  # 30 minutes
    
    # Security settings
    SSH_KEY_PATH: Path = Path.home() / ".ssh" / "aegis_cli"
    TOTP_SECRET_PATH: Path = Path.home() / ".aegis" / "totp_secret"
    
    # API settings
    API_BASE_PATH: str = "/api/v1"
    VERIFY_SSL: bool = True
    
    # CLI settings
    EDITOR: str = os.getenv("EDITOR", "nano")
    PAGER: str = os.getenv("PAGER", "less")
    
    # Logging
    LOG_FILE: Path = Path.home() / ".aegis" / "cli.log"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_prefix = "AEGIS_CLI_"
        case_sensitive = True


settings = CLISettings()


def ensure_config_dirs():
    """Ensure necessary directories exist"""
    aegis_dir = Path.home() / ".aegis"
    aegis_dir.mkdir(exist_ok=True, mode=0o700)
    
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(exist_ok=True, mode=0o700)
