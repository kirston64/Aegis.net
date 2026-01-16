"""
Authentication Service for Control Plane
Handles CLI authentication with SSH keys + TOTP
"""
import jwt
import pyotp
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import structlog

logger = structlog.get_logger()


class AuthService:
    """Authentication service for CLI access"""
    
    def __init__(self, 
                 authorized_keys: List[str],
                 whitelisted_ips: List[str],
                 jwt_secret: str,
                 session_timeout: int = 1800):
        """
        Initialize authentication service
        
        Args:
            authorized_keys: List of authorized SSH public keys
            whitelisted_ips: List of whitelisted IP addresses
            jwt_secret: Secret for JWT token generation
            session_timeout: Session timeout in seconds (default 30 min)
        """
        self.authorized_keys = set(authorized_keys)
        self.whitelisted_ips = set(whitelisted_ips)
        self.jwt_secret = jwt_secret
        self.session_timeout = session_timeout
        
        # In-memory TOTP secrets storage (in production, use database)
        self.totp_secrets: Dict[str, str] = {}
    
    def verify_ip(self, client_ip: str) -> bool:
        """Verify if IP is whitelisted"""
        if not self.whitelisted_ips:
            # If no whitelist configured, allow all (not recommended for production)
            return True
        
        is_allowed = client_ip in self.whitelisted_ips
        
        if not is_allowed:
            logger.warning("ip_not_whitelisted", client_ip=client_ip)
        
        return is_allowed
    
    def verify_ssh_key(self, public_key: str) -> bool:
        """Verify SSH public key"""
        # Normalize key (remove extra whitespace)
        normalized_key = " ".join(public_key.split())
        
        is_authorized = normalized_key in self.authorized_keys
        
        if not is_authorized:
            logger.warning("unauthorized_ssh_key", key_preview=public_key[:50])
        
        return is_authorized
    
    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        if user_id not in self.totp_secrets:
            logger.warning("totp_secret_not_found", user_id=user_id)
            return False
        
        secret = self.totp_secrets[user_id]
        totp = pyotp.TOTP(secret)
        
        # Verify with 1 window tolerance (30 seconds before/after)
        is_valid = totp.verify(token, valid_window=1)
        
        if not is_valid:
            logger.warning("invalid_totp_token", user_id=user_id)
        
        return is_valid
    
    def register_totp_secret(self, user_id: str, secret: str):
        """Register TOTP secret for a user"""
        self.totp_secrets[user_id] = secret
        logger.info("totp_secret_registered", user_id=user_id)
    
    def get_user_from_key(self, public_key: str) -> Optional[str]:
        """Extract user ID from SSH public key comment"""
        parts = public_key.strip().split()
        if len(parts) >= 3:
            return parts[2]  # Comment field (e.g., user@host)
        return "admin"  # Default user
    
    def create_session_token(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Create JWT session token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(seconds=self.session_timeout),
            "type": "cli_session"
        }
        
        if metadata:
            payload.update(metadata)
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        logger.info("session_token_created", user_id=user_id, expires_in=self.session_timeout)
        
        return token
    
    def verify_session_token(self, token: str) -> Dict:
        """Verify and decode JWT session token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            if payload.get("type") != "cli_session":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("session_token_expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please reconnect."
            )
        
        except jwt.InvalidTokenError as e:
            logger.warning("invalid_session_token", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            )
    
    def authenticate_cli(self, 
                        public_key: str, 
                        totp_token: str, 
                        client_ip: str) -> Dict[str, str]:
        """
        Full CLI authentication process
        
        Returns:
            Dict with access_token and user info
        
        Raises:
            HTTPException if authentication fails
        """
        # Step 1: Verify IP whitelist
        if not self.verify_ip(client_ip):
            logger.warning("cli_auth_failed_ip", client_ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address not whitelisted"
            )
        
        # Step 2: Verify SSH key
        if not self.verify_ssh_key(public_key):
            logger.warning("cli_auth_failed_key", client_ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SSH key not authorized"
            )
        
        # Step 3: Get user ID
        user_id = self.get_user_from_key(public_key)
        
        # Step 4: Verify TOTP
        if not self.verify_totp(user_id, totp_token):
            logger.warning("cli_auth_failed_totp", user_id=user_id, client_ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP token"
            )
        
        # Step 5: Create session token
        token = self.create_session_token(user_id, {
            "client_ip": client_ip,
            "auth_method": "ssh_key_totp"
        })
        
        logger.info("cli_auth_success", user_id=user_id, client_ip=client_ip)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_id,
            "expires_in": self.session_timeout
        }


# Global auth service instance (will be initialized in config)
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get global auth service instance"""
    global _auth_service
    if _auth_service is None:
        raise RuntimeError("Auth service not initialized")
    return _auth_service


def init_auth_service(authorized_keys: List[str], 
                     whitelisted_ips: List[str],
                     jwt_secret: str,
                     session_timeout: int = 1800):
    """Initialize global auth service"""
    global _auth_service
    _auth_service = AuthService(
        authorized_keys=authorized_keys,
        whitelisted_ips=whitelisted_ips,
        jwt_secret=jwt_secret,
        session_timeout=session_timeout
    )
    logger.info("auth_service_initialized", 
                authorized_keys_count=len(authorized_keys),
                whitelisted_ips_count=len(whitelisted_ips))
