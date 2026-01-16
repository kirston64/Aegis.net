"""
Setup script for 2FA authentication
"""
import click
from rich.console import Console
from rich.panel import Panel
from auth import auth_manager
from config import ensure_config_dirs

console = Console()


@click.command()
def setup():
    """Setup 2FA authentication for Aegis CLI"""
    console.print(Panel.fit(
        "[bold cyan]Aegis CLI - 2FA Setup[/bold cyan]\n"
        "This will generate SSH keys and TOTP secret for secure authentication",
        border_style="cyan"
    ))
    
    # Ensure directories exist
    ensure_config_dirs()
    
    # Setup SSH keys
    console.print("\n[bold]Step 1: SSH Keys[/bold]")
    ssh_key_path = auth_manager.setup_ssh_keys()
    
    # Setup TOTP
    console.print("\n[bold]Step 2: TOTP (Two-Factor Authentication)[/bold]")
    totp_secret = auth_manager.setup_totp()
    
    # Test TOTP
    console.print("\n[bold]Step 3: Verify Setup[/bold]")
    console.print("[cyan]Please enter the 6-digit code from your authenticator app to verify:[/cyan]")
    test_token = console.input("[yellow]TOTP Code: [/yellow]")
    
    if auth_manager.verify_totp(test_token):
        console.print("\n[green]✓ 2FA setup completed successfully![/green]")
        console.print("\n[yellow]Next steps:[/yellow]")
        console.print("1. Send your public SSH key to the Control Plane administrator")
        console.print(f"   Public key location: {ssh_key_path}.pub")
        console.print("2. Connect to Control Plane: aegis-cli connect <host>")
    else:
        console.print("\n[red]✗ TOTP verification failed. Please try setup again.[/red]")


if __name__ == "__main__":
    setup()
