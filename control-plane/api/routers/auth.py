"""
Authentication Router - CLI login endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Annotated
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from ..services.auth import get_auth_service, AuthService
from ..services.audit_logger import get_audit_logger, AuditLogger

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


class CLILoginRequest(BaseModel):
    """CLI login request"""
    public_key: str
    totp_token: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: str
    expires_in: int


@router.post("/cli-login", response_model=TokenResponse)
async def cli_login(
    request: Request,
    login_data: CLILoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Authenticate CLI client with SSH key + TOTP
    
    This endpoint performs multi-factor authentication:
    1. Verify SSH public key is authorized
    2. Verify TOTP token is valid
    3. Check IP whitelist
    4. Generate session JWT
    """
    
    # Get client IP
    client_ip = request.client.host
    
    try:
        # Perform authentication
        result = auth_service.authenticate_cli(
            public_key=login_data.public_key,
            totp_token=login_data.totp_token,
            client_ip=client_ip
        )
        
        # Audit log success
        audit_logger.log_action(
            user=result["user"],
            action="auth.cli_login",
            details={"method": "ssh_key_totp"},
            client_ip=client_ip,
            success=True
        )
        
        return TokenResponse(**result)
    
    except HTTPException as e:
        # Audit log failure
        audit_logger.log_action(
            user="unknown",
            action="auth.cli_login",
            details={"error": e.detail, "method": "ssh_key_totp"},
            client_ip=client_ip,
            success=False
        )
        raise


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Dependency to get current authenticated user from JWT
    
    Returns:
        User payload from JWT token
    
    Raises:
        HTTPException if token is invalid or expired
    """
    token = credentials.credentials
    payload = auth_service.verify_session_token(token)
    return payload
