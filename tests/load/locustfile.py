"""
Aegis.net — Load Testing Suite
================================
A comprehensive load testing tool using Locust to stress-test the Aegis.net
Control Plane API and simulate various traffic patterns.

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Web UI available at: http://localhost:8089
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import random
import uuid
import json
import time


# ============================================================================
#  Test Data
# ============================================================================

DOMAINS = [
    "example.com",
    "test-site.ru", 
    "myapp.io",
    "shop.example.com",
    "api.service.net",
    "blog.test.org",
]

COUNTRIES = ["RU", "DE", "US", "NL", "FR", "GB", "CN", "JP", "BR", "IN"]


# ============================================================================
#  User Behaviors
# ============================================================================

class HealthCheckUser(HttpUser):
    """
    Simulates monitoring systems hitting health endpoints.
    Very lightweight, just pings /health and /ready.
    """
    weight = 3
    wait_time = between(0.5, 2)
    
    @task(3)
    def check_health(self):
        """Hit the health endpoint"""
        self.client.get("/health", name="/health")
    
    @task(1)
    def check_ready(self):
        """Hit the readiness endpoint"""
        self.client.get("/ready", name="/ready")


class APIUser(HttpUser):
    """
    Simulates typical API usage: listing domains, checking stats.
    """
    weight = 5
    wait_time = between(1, 3)
    
    def on_start(self):
        """Create a test domain on startup"""
        self.domain_name = f"loadtest-{uuid.uuid4().hex[:8]}.example.com"
        self.client.post(
            "/api/v1/domains",
            json={
                "domain": self.domain_name,
                "origin_ip": f"10.0.{random.randint(1,255)}.{random.randint(1,255)}",
                "origin_port": 443
            },
            name="POST /api/v1/domains (create)"
        )
    
    @task(5)
    def list_domains(self):
        """List all domains with pagination"""
        page = random.randint(1, 5)
        self.client.get(
            f"/api/v1/domains?page={page}&per_page=20",
            name="GET /api/v1/domains"
        )
    
    @task(3)
    def get_domain_stats(self):
        """Get traffic statistics for a domain"""
        domain = random.choice(DOMAINS)
        with self.client.get(
            f"/api/v1/domains/{domain}/stats",
            name="GET /api/v1/domains/{domain}/stats",
            catch_response=True
        ) as response:
            # 404 is expected for non-existent domains
            if response.status_code == 404:
                response.success()
    
    @task(2)
    def get_domain_config(self):
        """Get domain details"""
        domain = random.choice(DOMAINS)
        with self.client.get(
            f"/api/v1/domains/{domain}",
            name="GET /api/v1/domains/{domain}",
            catch_response=True
        ) as response:
            if response.status_code == 404:
                response.success()
    
    def on_stop(self):
        """Cleanup: delete the test domain"""
        self.client.delete(
            f"/api/v1/domains/{self.domain_name}",
            name="DELETE /api/v1/domains/{domain}"
        )


class AggressiveUser(HttpUser):
    """
    Simulates aggressive traffic patterns (potential attacker behavior).
    Sends requests rapidly with minimal delay.
    """
    weight = 2
    wait_time = between(0.1, 0.5)  # Very fast requests
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health endpoint hits"""
        self.client.get("/health", name="/health [aggressive]")
    
    @task(5)
    def rapid_api_calls(self):
        """Rapid API calls"""
        self.client.get(
            "/api/v1/domains?page=1&per_page=100",
            name="GET /api/v1/domains [aggressive]"
        )
    
    @task(3)
    def spam_domain_creation(self):
        """Try to create many domains rapidly"""
        fake_domain = f"spam-{uuid.uuid4().hex[:12]}.evil.com"
        with self.client.post(
            "/api/v1/domains",
            json={
                "domain": fake_domain,
                "origin_ip": "192.168.1.1",
                "origin_port": 80
            },
            name="POST /api/v1/domains [spam]",
            catch_response=True
        ) as response:
            # Clean up immediately
            pass


class AttackModeUser(HttpUser):
    """
    Tests the attack mode functionality.
    Simulates dashboard users toggling protection levels.
    """
    weight = 1
    wait_time = between(2, 5)
    
    @task(3)
    def get_attack_mode(self):
        """Check current attack mode status"""
        domain = random.choice(DOMAINS)
        with self.client.get(
            f"/api/v1/attack-mode/{domain}",
            name="GET /api/v1/attack-mode/{domain}",
            catch_response=True
        ) as response:
            if response.status_code == 404:
                response.success()
    
    @task(1)
    def toggle_attack_mode(self):
        """Toggle attack mode on a domain"""
        domain = random.choice(DOMAINS)
        mode = random.choice(["off", "low", "medium", "high", "under_attack"])
        with self.client.put(
            f"/api/v1/attack-mode/{domain}",
            json={"mode": mode},
            name="PUT /api/v1/attack-mode/{domain}",
            catch_response=True
        ) as response:
            if response.status_code in [404, 422]:
                response.success()


# ============================================================================
#  Event Handlers
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a new load test starts"""
    print("=" * 60)
    print("  🚀 Aegis.net Load Test Starting")
    print("=" * 60)
    print(f"  Target: {environment.host}")
    print(f"  User classes: HealthCheckUser, APIUser, AggressiveUser, AttackModeUser")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops"""
    print("\n" + "=" * 60)
    print("  ✅ Aegis.net Load Test Complete")
    print("=" * 60)


# ============================================================================
#  Spike Test Shape (Optional)
# ============================================================================

from locust import LoadTestShape

class SpikeTestShape(LoadTestShape):
    """
    A load test shape that simulates a traffic spike.
    
    To use this shape, run:
        locust -f locustfile.py --host=http://localhost:8000 --headless
    
    Timeline:
    - 0-30s:   Ramp from 0 to 50 users (normal load)
    - 30-60s:  Hold at 50 users
    - 60-90s:  Spike to 200 users (attack simulation)
    - 90-120s: Hold at 200 users
    - 120-150s: Ramp down to 50 users
    - 150-180s: Ramp down to 0
    """
    
    stages = [
        {"duration": 30, "users": 50, "spawn_rate": 2},
        {"duration": 30, "users": 50, "spawn_rate": 1},
        {"duration": 30, "users": 200, "spawn_rate": 10},
        {"duration": 30, "users": 200, "spawn_rate": 1},
        {"duration": 30, "users": 50, "spawn_rate": 5},
        {"duration": 30, "users": 0, "spawn_rate": 5},
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            stage["duration"]
            if run_time < sum(s["duration"] for s in self.stages[:self.stages.index(stage) + 1]):
                return (stage["users"], stage["spawn_rate"])
        
        return None
