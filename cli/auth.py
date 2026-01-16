"""
Authentication Module - SSH Keys + TOTP 2FA
"""
import pyotp
import json
import qrcode
import jwt
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from rich.console import Console
from rich.prompt import Prompt
from .config import settings

console = Console()


class AuthManager:
    """Manages authentication for CLI"""
    
    def __init__(self):
        self.ssh_key_path = settings.SSH_KEY_PATH
        self.totp_secret_path = settings.TOTP_SECRET_PATH
        self._totp = None
        self._totp = None
        self._current_token = None
        self._host = None
        self._port = None
        
        self.load_session()
    
    def setup_ssh_keys(self) -> Path:
        """Generate SSH key pair if not exists"""
        if self.ssh_key_path.exists():
            console.print(f"[yellow]SSH key already exists: {self.ssh_key_path}[/yellow]")
            return self.ssh_key_path
        
        console.print("[cyan]Generating new SSH key pair...[/cyan]")
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Write private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        self.ssh_key_path.write_bytes(private_pem)
        self.ssh_key_path.chmod(0o600)
        
        # Write public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        
        pub_key_path = Path(str(self.ssh_key_path) + ".pub")
        pub_key_path.write_bytes(public_pem)
        
        console.print(f"[green]✓ SSH keys generated successfully[/green]")
        console.print(f"[cyan]Private key: {self.ssh_key_path}[/cyan]")
        console.print(f"[cyan]Public key: {pub_key_path}[/cyan]")
        console.print("\n[yellow]⚠ Add this public key to Control Plane authorized_keys:[/yellow]")
        console.print(f"[white]{public_pem.decode()}[/white]")
        
        return self.ssh_key_path
    
    def setup_totp(self) -> str:
        """Setup TOTP 2FA and generate QR code"""
        if self.totp_secret_path.exists():
            console.print("[yellow]TOTP already configured[/yellow]")
            return self.totp_secret_path.read_text().strip()
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Save secret
        self.totp_secret_path.parent.mkdir(parents=True, exist_ok=True)
        self.totp_secret_path.write_text(secret)
        self.totp_secret_path.chmod(0o600)
        
        # Generate provisioning URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name="Aegis CLI",
            issuer_name="Aegis.net"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        console.print("\n[green]✓ TOTP 2FA configured successfully[/green]")
        console.print("\n[yellow]Scan this QR code with Google Authenticator:[/yellow]\n")
        qr.print_ascii()
        
        console.print(f"\n[cyan]Or enter this secret manually: {secret}[/cyan]")
        
        return secret
    
    def verify_totp(self, token: str) -> bool:
        """Verify TOTP token"""
        if not self.totp_secret_path.exists():
            console.print("[red]✗ TOTP not configured. Run setup first.[/red]")
            return False
        
        secret = self.totp_secret_path.read_text().strip()
        totp = pyotp.TOTP(secret)
        
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid:
            console.print("[green]✓ TOTP verified[/green]")
        else:
            console.print("[red]✗ Invalid TOTP token[/red]")
        
        return is_valid
    
    def get_ssh_public_key(self) -> str:
        """Get SSH public key for authentication"""
        pub_key_path = Path(str(self.ssh_key_path) + ".pub")
        
        if not pub_key_path.exists():
            raise FileNotFoundError("SSH public key not found. Run setup first.")
        
        return pub_key_path.read_text().strip()
    
    def create_session_token(self, control_plane_response: dict) -> str:
        """Create and store session token from Control Plane response"""
        # Store token received from Control Plane
        self._current_token = control_plane_response.get("access_token")
        
        # Save session to file
        self.save_session({
            "token": self._current_token,
            "user": control_plane_response.get("user"),
            "expires_in": control_plane_response.get("expires_in")
        })
        
        return self._current_token
    
    def get_session_token(self) -> Optional[str]:
        """Get current session token"""
        return self._current_token
    
    def clear_session(self):
        """Clear current session"""
        self._current_token = None
        self._host = None
        self._port = None
        
        if settings.SESSION_FILE_PATH.exists():
            settings.SESSION_FILE_PATH.unlink()
            
        console.print("[yellow]Session cleared[/yellow]")

    def save_session(self, data: dict):
        """Save session data to file"""
        if self._host:
            data["host"] = self._host
        if self._port:
            data["port"] = self._port
            
        settings.SESSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        settings.SESSION_FILE_PATH.write_text(json.dumps(data))
        
    def load_session(self):
        """Load session from file"""
        if not settings.SESSION_FILE_PATH.exists():
            return
            
        try:
            data = json.loads(settings.SESSION_FILE_PATH.read_text())
            self._current_token = data.get("token")
            self._host = data.get("host")
            self._port = data.get("port")
        except Exception:
            # Invalid session file
            pass

    def set_connection_info(self, host: str, port: int):
        """Set connection info for session"""
        self._host = host
        self._port = port
    
    def prompt_totp(self) -> str:
        """Prompt user for TOTP code"""
        return Prompt.ask("[cyan]Enter TOTP code from authenticator app[/cyan]")


# Global auth manager instance
auth_manager = AuthManager()
