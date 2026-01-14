"""
Aegis.net Website Load Test
============================
Simulates DDoS attack on the Aegis.net landing page.
"""

from locust import HttpUser, task, between, events
import random


class WebsiteUser(HttpUser):
    """
    Normal website visitor behavior.
    """
    weight = 5
    wait_time = between(1, 3)
    
    @task(10)
    def load_homepage(self):
        """Load main page"""
        self.client.get("/", name="Homepage")
    
    @task(5)
    def load_css(self):
        """Load stylesheet"""
        self.client.get("/styles.css", name="CSS")
    
    @task(5)
    def load_js(self):
        """Load JavaScript"""
        self.client.get("/script.js", name="JavaScript")


class AggressiveAttacker(HttpUser):
    """
    Simulates aggressive DDoS traffic.
    Rapid requests with minimal delay.
    """
    weight = 3
    wait_time = between(0.05, 0.2)  # Very fast!
    
    @task(10)
    def flood_homepage(self):
        """Flood homepage with requests"""
        self.client.get("/", name="Homepage [ATTACK]")
    
    @task(5)
    def flood_assets(self):
        """Flood static assets"""
        asset = random.choice(["/styles.css", "/script.js", "/index.html"])
        self.client.get(asset, name=f"Asset [ATTACK]")


class SlowlorisAttacker(HttpUser):
    """
    Simulates Slowloris-style attack.
    Holds connections open with slow requests.
    """
    weight = 2
    wait_time = between(5, 10)  # Slow, holding connections
    
    @task
    def slow_request(self):
        """Slow request to hold connection"""
        self.client.get("/", name="Slowloris", timeout=30)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("  🔥 AEGIS.NET WEBSITE ATTACK SIMULATION")
    print("=" * 60)
    print(f"  Target: {environment.host}")
    print("  Attack types: Flood, Asset Flood, Slowloris")
    print("=" * 60)
