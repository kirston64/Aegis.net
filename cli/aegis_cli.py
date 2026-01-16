#!/usr/bin/env python3
"""
Aegis CLI - Main command interface
Secure management tool for Aegis.net DDoS protection
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from typing import Optional
import sys

from .config import ensure_config_dirs, settings
from .auth import auth_manager
from .api_client import ControlPlaneClient

console = Console()


class CLIContext:
    """CLI context manager"""
    def __init__(self):
        self.client: Optional[ControlPlaneClient] = None
        self.connected = False


pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.version_option(version="1.0.0", prog_name="aegis-cli")
def cli():
    """Aegis CLI - Secure management for DDoS protection"""
    """Aegis CLI - Secure management for DDoS protection"""
    ensure_config_dirs()
    
    # Try to restore session
    ctx = click.get_current_context().obj
    if auth_manager._host and auth_manager._current_token:
        # Initialize client with stored connection info
        try:
            ctx.client = ControlPlaneClient(
                host=auth_manager._host, 
                port=auth_manager._port or 8000
            )
            ctx.connected = True
        except Exception:
            # Failed to restore connection
            pass


@cli.command()
@click.argument("host")
@click.option("--port", "-p", default=8000, help="Control Plane port")
@click.option("--ssl/--no-ssl", default=False, help="Use SSL connection")
@pass_context
def connect(ctx: CLIContext, host: str, port: int, ssl: bool):
    """Connect to Aegis Control Plane"""
    console.print(Panel.fit(
        f"[bold cyan]Connecting to Control Plane[/bold cyan]\n{host}:{port}",
        border_style="cyan"
    ))
    
    try:
        # Get SSH public key
        try:
            public_key = auth_manager.get_ssh_public_key()
        except FileNotFoundError:
            console.print("[yellow]SSH key not found. Run setup first:[/yellow]")
            console.print("[cyan]python cli/setup_2fa.py[/cyan]")
            sys.exit(1)
        
        # Prompt for TOTP
        totp_token = auth_manager.prompt_totp()
        
        # Set connection info
        auth_manager.set_connection_info(host, port)
        
        # Create client and authenticate
        ctx.client = ControlPlaneClient(host, port, ssl)
        
        with console.status("[cyan]Authenticating...[/cyan]"):
            response = ctx.client.authenticate(public_key, totp_token)
        
        ctx.connected = True
        
        console.print(f"\n[green]✓ Connected successfully![/green]")
        console.print(f"[dim]User: {response.get('user', 'admin')}[/dim]")
        console.print(f"[dim]Session expires in: {settings.SESSION_TIMEOUT_SECONDS // 60} minutes[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        sys.exit(1)


@cli.group()
def domain():
    """Manage domains"""
    pass


@domain.command("list")
@pass_context
def domain_list(ctx: CLIContext):
    """List all protected domains"""
    _ensure_connected(ctx)
    
    try:
        with console.status("[cyan]Fetching domains...[/cyan]"):
            response = ctx.client.get("domains")
        
        domains = response.get("domains", [])
        
        if not domains:
            console.print("[yellow]No domains configured[/yellow]")
            return
        
        table = Table(title="Protected Domains", box=box.ROUNDED)
        table.add_column("Domain", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Protection Level", style="yellow")
        table.add_column("Requests/Day", style="blue")
        
        for d in domains:
            table.add_row(
                d.get("name", ""),
                "✓ Active" if d.get("active") else "○ Inactive",
                str(d.get("protection_level", 1)),
                f"{d.get('requests_today', 0):,}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch domains: {e}[/red]")


@domain.command("add")
@click.argument("domain_name")
@click.option("--origin", "-o", required=True, help="Origin server URL")
@click.option("--protection", "-p", default=1, type=int, help="Initial protection level (1-5)")
@pass_context
def domain_add(ctx: CLIContext, domain_name: str, origin: str, protection: int):
    """Add a new domain"""
    _ensure_connected(ctx)
    
    if not (1 <= protection <= 5):
        console.print("[red]Protection level must be between 1 and 5[/red]")
        return
    
    try:
        with console.status(f"[cyan]Adding domain {domain_name}...[/cyan]"):
            response = ctx.client.post("domains", {
                "domain": domain_name,
                "origin": origin,
                "protection_level": protection
            })
        
        console.print(f"[green]✓ Domain {domain_name} added successfully[/green]")
        console.print(f"[dim]Protection level: {protection}[/dim]")
        console.print(f"[dim]Origin: {origin}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to add domain: {e}[/red]")


@domain.command("delete")
@click.argument("domain_name")
@pass_context
def domain_delete(ctx: CLIContext, domain_name: str):
    """Delete a domain"""
    _ensure_connected(ctx)
    
    try:
        if not click.confirm(f"Are you sure you want to delete {domain_name}?"):
            return
            
        with console.status(f"[cyan]Deleting domain {domain_name}...[/cyan]"):
            ctx.client.delete(f"domains/{domain_name}")
        
        console.print(f"[green]✓ Domain {domain_name} deleted successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to delete domain: {e}[/red]")


@cli.group()
def ratelimit():
    """Manage rate limiting"""
    pass


@ratelimit.command("set")
@click.argument("domain_name")
@click.option("--rps", type=int, help="Requests per second (global)")
@click.option("--rpm", type=int, help="Requests per minute (global)")
@click.option("--per-ip-rps", type=int, help="Requests per second per IP")
@click.option("--per-ip-rpm", type=int, help="Requests per minute per IP")
@click.option("--burst", type=int, default=10, help="Burst allowance")
@pass_context
def ratelimit_set(ctx: CLIContext, domain_name: str, rps: Optional[int], 
                  rpm: Optional[int], per_ip_rps: Optional[int], 
                  per_ip_rpm: Optional[int], burst: int):
    """Configure rate limiting for a domain"""
    _ensure_connected(ctx)
    
    config = {
        "domain": domain_name,
        "burst_allowance": burst
    }
    
    if rps:
        config["requests_per_second"] = rps
    if rpm:
        config["requests_per_minute"] = rpm
    if per_ip_rps:
        config["per_ip_rps"] = per_ip_rps
    if per_ip_rpm:
        config["per_ip_rpm"] = per_ip_rpm
    
    try:
        with console.status(f"[cyan]Configuring rate limits for {domain_name}...[/cyan]"):
            response = ctx.client.post("ratelimit/config", config)
        
        console.print(f"[green]✓ Rate limiting configured for {domain_name}[/green]")
        
        # Display configuration
        table = Table(title=f"Rate Limit Configuration: {domain_name}", box=box.SIMPLE)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="yellow")
        
        if rps:
            table.add_row("Global RPS", f"{rps:,}")
        if rpm:
            table.add_row("Global RPM", f"{rpm:,}")
        if per_ip_rps:
            table.add_row("Per-IP RPS", f"{per_ip_rps}")
        if per_ip_rpm:
            table.add_row("Per-IP RPM", f"{per_ip_rpm}")
        table.add_row("Burst Allowance", f"{burst}")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to configure rate limiting: {e}[/red]")


@ratelimit.command("show")
@click.argument("domain_name")
@pass_context
def ratelimit_show(ctx: CLIContext, domain_name: str):
    """Show rate limiting configuration"""
    _ensure_connected(ctx)
    
    try:
        with console.status(f"[cyan]Fetching rate limit config for {domain_name}...[/cyan]"):
            response = ctx.client.get(f"ratelimit/config/{domain_name}")
        
        config = response.get("config", {})
        
        table = Table(title=f"Rate Limit Configuration: {domain_name}", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Global RPS", f"{config.get('requests_per_second', 'Not set'):,}")
        table.add_row("Global RPM", f"{config.get('requests_per_minute', 'Not set'):,}")
        table.add_row("Per-IP RPS", f"{config.get('per_ip_rps', 'Not set')}")
        table.add_row("Per-IP RPM", f"{config.get('per_ip_rpm', 'Not set')}")
        table.add_row("Burst Allowance", f"{config.get('burst_allowance', 0)}")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch rate limit config: {e}[/red]")


@cli.group()
def protection():
    """Manage protection levels"""
    pass


@protection.command("set")
@click.argument("domain_name")
@click.argument("level", type=int)
@pass_context
def protection_set(ctx: CLIContext, domain_name: str, level: int):
    """Set protection level for a domain (1-5)"""
    _ensure_connected(ctx)
    
    if not (1 <= level <= 5):
        console.print("[red]Protection level must be between 1 and 5[/red]")
        return
    
    try:
        with console.status(f"[cyan]Setting protection level to {level}...[/cyan]"):
            response = ctx.client.put(f"attack-mode/{domain_name}", {
                "level": level
            })
        
        console.print(f"[green]✓ Protection level set to {level} for {domain_name}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to set protection level: {e}[/red]")


@cli.command()
@click.argument("domain_name")
@pass_context
def stats(ctx: CLIContext, domain_name: str):
    """Show statistics for a domain"""
    _ensure_connected(ctx)
    
    try:
        with console.status(f"[cyan]Fetching statistics for {domain_name}...[/cyan]"):
            response = ctx.client.get(f"stats/{domain_name}")
        
        stats_data = response.get("stats", {})
        
        # Main stats panel
        table = Table(title=f"Statistics: {domain_name}", box=box.ROUNDED, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Total Requests", f"{stats_data.get('total_requests', 0):,}")
        table.add_row("Blocked Requests", f"{stats_data.get('blocked_requests', 0):,}")
        table.add_row("Requests/sec", f"{stats_data.get('rps', 0):.2f}")
        table.add_row("Protection Level", f"{stats_data.get('protection_level', 1)}")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch statistics: {e}[/red]")


@cli.command()
@pass_context
def audit(ctx: CLIContext):
    """Show audit log"""
    _ensure_connected(ctx)
    
    try:
        with console.status("[cyan]Fetching audit log...[/cyan]"):
            response = ctx.client.get("audit/log")
        
        logs = response.get("logs", [])
        
        if not logs:
            console.print("[yellow]No audit logs available[/yellow]")
            return
        
        table = Table(title="Audit Log", box=box.ROUNDED)
        table.add_column("Timestamp", style="cyan")
        table.add_column("User", style="yellow")
        table.add_column("Action", style="green")
        table.add_column("Details", style="dim")
        
        for log in logs[:50]:  # Show last 50 entries
            table.add_row(
                log.get("timestamp", ""),
                log.get("user", ""),
                log.get("action", ""),
                log.get("details", "")
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch audit log: {e}[/red]")


def _ensure_connected(ctx: CLIContext):
    """Ensure client is connected"""
    if not ctx.client or not ctx.connected:
        console.print("[red]✗ Not connected. Run 'aegis-cli connect <host>' first[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli(obj=CLIContext())
