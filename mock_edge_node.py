import http.server
import socketserver
import time
import urllib.request
import urllib.error
import json
import threading

# Configuration
EDGE_PORT = 8080
ORIGIN_URL = "http://localhost:9000"
PROTECTION_TEMPLATE_PATH = "website/protection.html"

# Global Statistics & State
stats = {
    "total_requests": 0,
    "blocked_requests": 0,
    "start_time": time.time(),
}
# Instantaneous stats (reset every second)
current_window = {
    "requests": 0,
    "blocked": 0
}
# Exposed generic Metrics
metrics = {
    "rps": 0,
    "blocked_rps": 0
}

# Config
config = {
    "protection_level": 1, # 0=Observe, 1=Soft, 2=Medium, 3=Hard, 4=Lockdown
    "rate_limit": 50 # Requests per second per IP
}

history_lock = threading.Lock()

# Rate Limiting State
rate_limits = {}
WINDOW = 1.0

# Background thread to calculate RPS
def update_history_loop():
    while True:
        time.sleep(1)
        with history_lock:
            # Snapshot current window to metrics
            metrics["rps"] = current_window["requests"]
            metrics["blocked_rps"] = current_window["blocked"]
            
            # Reset window
            current_window["requests"] = 0
            current_window["blocked"] = 0

class AegisEdgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # API Endpoint for Dashboard
        if self.path == "/api/stats":
            self.handle_api_stats()
            return
            
        if self.path == "/api/config":
            self.handle_get_config()
            return

        # Determine Client IP (Enable spoofing for testing)
        client_ip = self.client_address[0]
        if "X-Forwarded-For" in self.headers:
            # Take the first IP in the list
            client_ip = self.headers["X-Forwarded-For"].split(",")[0].strip()
        
        # Track Request
        with history_lock:
            stats["total_requests"] += 1
            current_window["requests"] += 1

    # 1. Protection Logic / JS Challenge
        action = self.decide_action(client_ip)
        
        if action == "BLOCK":
            with history_lock:
                stats["blocked_requests"] += 1
                current_window["blocked"] += 1
                # Mock Attack Data for War Room
                self.record_attack(client_ip, "BLOCK")
            self.serve_protection_page(client_ip, "Aegis Firewall Block")
            return

        if action == "CHALLENGE":
             # Check for cookie
            if "aegis_passed=1" not in self.headers.get("Cookie", ""):
                 with history_lock:
                    current_window["blocked"] += 1 # Count as 'mitigated'
                    self.record_attack(client_ip, "CHALLENGE")
                 self.serve_js_challenge(client_ip)
                 return

        # 2. Proxy to Origin
        self.proxy_request()

    def do_POST(self):
        if self.path == "/api/config":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                new_config = json.loads(post_data)
                
                with history_lock:
                    if "protection_level" in new_config:
                        config["protection_level"] = int(new_config["protection_level"])
                        # Adjust rate limits based on level
                        if config["protection_level"] == 0: config["rate_limit"] = 1000
                        elif config["protection_level"] == 1: config["rate_limit"] = 100
                        elif config["protection_level"] == 2: config["rate_limit"] = 50
                        elif config["protection_level"] == 3: config["rate_limit"] = 10 # Anti-Bot Mode
                        elif config["protection_level"] == 4: config["rate_limit"] = 0
                    
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "config": config}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Invalid JSON: {str(e)}")
            return
            
        self.send_error(404)

    def handle_api_stats(self):
        """Serve JSON stats for the Dashboard"""
        # Get recent attacks (last 20)
        recent = []
        with history_lock:
             recent = list(stats.get("recent_attacks", []))[-20:]

        data = {
            "total": stats["total_requests"],
            "blocked": stats["blocked_requests"],
            "rps": metrics["rps"],
            "blocked_rps": metrics["blocked_rps"],
            "active_ips": len(rate_limits),
            "config": config,
            "recent_attacks": recent,
            "status": "active"
        }
        
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def handle_get_config(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(config).encode("utf-8"))

    def decide_action(self, ip):
        level = config["protection_level"]
        limit = config["rate_limit"]
        
        # Level 4: Lockdown
        if level == 4: return "BLOCK"
        
        # Rate Limiting
        is_limited = self.is_rate_limited(ip, limit)
        
        if is_limited:
            # Level 3 is "Under Attack" -> Use Challenge instead of hard block initially? 
            # For simplicity, if rate limited at level 3, we block. 
            # But let's say Level 3 ALWAYS challenges new IPs first.
            if level == 3: return "CHALLENGE" 
            return "BLOCK"
            
        # Level 3: "Under Attack" / Anti-Bot Mode - Challenge everyone not whitelisted (cookie)
        if level == 3:
             return "CHALLENGE"
             
        return "ALLOW"

    def is_rate_limited(self, ip, limit):
        now = time.time()
        record = rate_limits.get(ip)
        
        if not record:
            rate_limits[ip] = {"count": 1, "start": now}
            return False
            
        if now - record["start"] > WINDOW:
            # Reset window
            record["count"] = 1
            record["start"] = now
            return False
        
        record["count"] += 1
        if record["count"] > limit:
            return True
            
        return False

    def record_attack(self, ip, type):
        # Mock Geo Data
        import random
        countries = [
            {"code": "CN", "name": "China", "coords": [104.1954, 35.8617]},
            {"code": "RU", "name": "Russia", "coords": [105.3188, 61.5240]},
            {"code": "US", "name": "USA", "coords": [-95.7129, 37.0902]},
            {"code": "BR", "name": "Brazil", "coords": [-51.9253, -14.2350]},
            {"code": "DE", "name": "Germany", "coords": [10.4515, 51.1657]},
            {"code": "IN", "name": "India", "coords": [78.9629, 20.5937]},
        ]
        target = random.choice(countries)
        
        # Jitter coords slightly
        lon = target["coords"][0] + random.uniform(-5, 5)
        lat = target["coords"][1] + random.uniform(-5, 5)
        
        attack = {
            "id": int(time.time() * 1000) + random.randint(0, 1000),
            "timestamp": time.time(),
            "ip": ip,
            "country": target["code"],
            "country_name": target["name"],
            "coordinates": [lon, lat], # GeoJSON uses [Lon, Lat]
            "type": type
        }
        
        if "recent_attacks" not in stats:
            stats["recent_attacks"] = []
            
        stats["recent_attacks"].append(attack)
        # Keep last 50
        if len(stats["recent_attacks"]) > 50:
             stats["recent_attacks"].pop(0)

    def serve_js_challenge(self, ip):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Aegis Security Check</title>
            <style>
                body { background: #111; color: #eee; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .box { text-align: center; padding: 40px; border: 1px solid #333; border-radius: 8px; background: #1a1a1a; }
                .spinner { border: 4px solid #333; border-top: 4px solid #00ff88; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>Aegis DDoS Protection</h1>
                <div class="spinner"></div>
                <p>Checking your browser...</p>
                <p style="color: #666; font-size: 12px; margin-top: 20px;">DDoS protection by Aegis.net</p>
            </div>
            <script>
                setTimeout(function() {
                    document.cookie = "aegis_passed=1; path=/; max-age=3600";
                    window.location.reload();
                }, 2000); // 2 second delay logic
            </script>
        </body>
        </html>
        """
        self.send_response(503) # Service Unavailable (standard for challenges)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def serve_protection_page(self, ip, reason):
        # Read template
        content = ""
        try:
            with open(PROTECTION_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = f"<h1>Aegis Protection</h1><p>Blocked: {reason}</p>"

        # Dynamic Replacement
        content = content.replace("Your IP", ip)
        content = content.replace("8a7b3c9d1e2f", f"mock-{int(time.time())}")
        content = content.replace("Мы зафиксировали аномальную активность", f"Access Denied<br>Reason: {reason}")
        
        self.send_response(403)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def proxy_request(self):
        try:
            req = urllib.request.Request(f"{ORIGIN_URL}{self.path}")
            # Forward headers...
            if 'User-Agent' in self.headers:
                req.add_header('User-Agent', self.headers['User-Agent'])
            
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.getcode())
                # Copy headers
                for k, v in resp.info().items():
                    if k.lower() not in ['transfer-encoding', 'content-encoding', 'server']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
            
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception:
            self.send_error(502, "Bad Gateway - Origin Down")

def run_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    
    # Start Stats Thread
    t = threading.Thread(target=update_history_loop, daemon=True)
    t.start()
    
    print(f"==================================================")
    print(f"🛡️  AEGIS EDGE SIMULATOR + API running on port {EDGE_PORT}")
    print(f"👉  API Stats:  http://localhost:{EDGE_PORT}/api/stats")
    print(f"👉  Origin:     {ORIGIN_URL}")
    print(f"==================================================")
    
    try:
        with socketserver.ThreadingTCPServer(("", EDGE_PORT), AegisEdgeHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    except OSError as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    run_server()
