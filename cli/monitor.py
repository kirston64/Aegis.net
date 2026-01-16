"""
Aegis CLI - Monitoring Command
Real-time monitoring dashboard in terminal
"""
import click
import requests
import time
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from datetime import datetime

console = Console()


@click.command()
@click.option('--interval', default=2, help='Refresh interval in seconds')
@click.option('--prometheus-url', default='http://localhost:9090', help='Prometheus URL')
def monitor(interval, prometheus_url):
    """Real-time monitoring dashboard"""
    
    def query_prometheus(query):
        """Query Prometheus for metrics"""
        try:
            response = requests.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=2
            )
            if response.status_code == 200:
                result = response.json()
                if result['data']['result']:
                    return float(result['data']['result'][0]['value'][1])
        except:
            pass
        return 0
    
    def generate_dashboard():
        """Generate dashboard layout"""
        layout = Layout()
        
        # Get metrics
        total_rps = query_prometheus('rate(nginx_http_requests_total[1m])')
        blocked_rps = query_prometheus('rate(nginx_http_requests_total{status="503"}[1m])')
        allowed_rps = total_rps - blocked_rps
        block_rate = (blocked_rps / total_rps * 100) if total_rps > 0 else 0
        
        cpu_usage = query_prometheus('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
        mem_total = query_prometheus('node_memory_MemTotal_bytes')
        mem_available = query_prometheus('node_memory_MemAvailable_bytes')
        mem_usage = ((mem_total - mem_available) / mem_total * 100) if mem_total > 0 else 0
        
        # Create table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold", width=20)
        table.add_column(style="white")
        
        table.add_row("🌐 Total RPS:", f"{total_rps:.1f} req/s")
        table.add_row("🛡️  Blocked:", f"{blocked_rps:.1f} req/s ({block_rate:.1f}%)")
        table.add_row("✅ Allowed:", f"{allowed_rps:.1f} req/s")
        table.add_row("", "")
        table.add_row("💻 CPU Usage:", f"{cpu_usage:.1f}%")
        table.add_row("🧠 Memory:", f"{mem_usage:.1f}%")
        
        panel = Panel(
            table,
            title=f"[bold cyan]AEGIS.NET — LIVE MONITORING[/bold cyan]",
            subtitle=f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]",
            border_style="cyan"
        )
        
        return panel
    
    console.print("[cyan]Starting monitoring... Press Ctrl+C to stop[/cyan]\n")
    
    try:
        with Live(generate_dashboard(), refresh_per_second=1/interval, console=console) as live:
            while True:
                time.sleep(interval)
                live.update(generate_dashboard())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


if __name__ == '__main__':
    monitor()
