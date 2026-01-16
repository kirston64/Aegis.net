"""
API Client for Control Plane communication
"""
import httpx
from typing import Optional, Dict, Any
from rich.console import Console
from .config import settings
from .auth import auth_manager

console = Console()


class ControlPlaneClient:
    """Client for communicating with Aegis Control Plane"""
    
    def __init__(self, host: str, port: int = 8000, use_ssl: bool = False):
        self.base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"
        self.api_base = f"{self.base_url}{settings.API_BASE_PATH}"
        self._client = httpx.Client(verify=settings.VERIFY_SSL, timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Aegis-CLI/1.0"
        }
        
        token = auth_manager.get_session_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers
    
    def authenticate(self, public_key: str, totp_token: str) -> Dict[str, Any]:
        """Authenticate with Control Plane"""
        try:
            response = self._client.post(
                f"{self.api_base}/auth/cli-login",
                json={
                    "public_key": public_key,
                    "totp_token": totp_token
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Store session token
            auth_manager.create_session_token(data)
            
            return data
        except httpx.HTTPStatusError as e:
            console.print(f"[red]Authentication failed: {e.response.status_code}[/red]")
            if e.response.status_code == 401:
                console.print("[yellow]Check your SSH key and TOTP token[/yellow]")
            raise
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            raise
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request to Control Plane"""
        try:
            response = self._client.get(
                f"{self.api_base}/{endpoint}",
                headers=self._get_headers(),
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise
    
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """POST request to Control Plane"""
        try:
            response = self._client.post(
                f"{self.api_base}/{endpoint}",
                headers=self._get_headers(),
                json=data,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise
    
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """PUT request to Control Plane"""
        try:
            response = self._client.put(
                f"{self.api_base}/{endpoint}",
                headers=self._get_headers(),
                json=data,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request to Control Plane"""
        try:
            response = self._client.delete(
                f"{self.api_base}/{endpoint}",
                headers=self._get_headers(),
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise
    
    def _handle_error(self, error: httpx.HTTPStatusError):
        """Handle HTTP errors"""
        status_code = error.response.status_code
        
        if status_code == 401:
            console.print("[red]✗ Authentication required. Please reconnect.[/red]")
            auth_manager.clear_session()
        elif status_code == 403:
            console.print("[red]✗ Access denied. Insufficient permissions.[/red]")
        elif status_code == 404:
            console.print("[yellow]✗ Resource not found[/yellow]")
        elif status_code == 429:
            console.print("[yellow]✗ Rate limit exceeded. Please wait.[/yellow]")
        elif status_code >= 500:
            console.print(f"[red]✗ Server error: {status_code}[/red]")
        else:
            console.print(f"[red]✗ Request failed: {status_code}[/red]")
        
        # Try to parse error message
        try:
            error_data = error.response.json()
            if "detail" in error_data:
                console.print(f"[dim]{error_data['detail']}[/dim]")
        except:
            pass
    
    def close(self):
        """Close client connection"""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
