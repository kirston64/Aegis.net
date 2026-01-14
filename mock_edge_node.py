import http.server
import socketserver
import time
import urllib.request
import urllib.error
import json
import threading

# Configuration
EDGE_PORT = 8080
ORIGIN_URL = "http://localhost:3000"
PROTECTION_TEMPLATE_PATH = "website/protection.html"

# Global Statistics
stats = {
    "total_requests": 0,
    "blocked_requests": 0,
    "start_time": time.time(),
    "history": [], # Last 60 seconds
}
history_lock = threading.Lock()

# Rate Limiting State
rate_limits = {}
RATE_LIMIT = 50 
WINDOW = 1.0

# Background thread to update history
def update_history_loop():
    while True:
        time.sleep(1)
        with history_lock:
            # Calculate current RPS based on difference from last check
            # For simplicity in this mock, we'll just push current snapshot
            # A real system would use a rolling window
            
            # Simple simulation: just take current counts (delta would be better)
            # but let's just tracking instantaneous RPS in the handler
            pass

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

        client_ip = self.client_address[0]
        
        # Track Request
        with history_lock:
            stats["total_requests"] += 1

        # 1. Rate Limiting Logic
        if self.is_rate_limited(client_ip):
            with history_lock:
                stats["blocked_requests"] += 1
            self.serve_protection_page(client_ip, "Rate Limit Exceeded")
            return

        # 2. Proxy to Origin
        self.proxy_request()

    def handle_api_stats(self):
        """Serve JSON stats for the Dashboard"""
        uptime = time.time() - stats["start_time"]
        
        # Calculate naive global RPS (total / uptime) - rough estimate
        rps = 0
        if uptime > 0:
            rps = stats["total_requests"] / uptime
            
        data = {
            "total": stats["total_requests"],
            "blocked": stats["blocked_requests"],
            "rps": int(rps), # Smoothed
            "active_ips": len(rate_limits),
            "status": "active"
        }
        
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def is_rate_limited(self, ip):
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
        if record["count"] > RATE_LIMIT:
            return True
            
        return False

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
        content = content.replace("Мы зафиксировали аномальную активность", f"Aegis Block: {reason}")

        self.send_response(429)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))
        # print(f"🛡️ [BLOCKED] {ip} - {reason}") # Noise reduction

    def proxy_request(self):
        try:
            req = urllib.request.Request(f"{ORIGIN_URL}{self.path}")
            if 'User-Agent' in self.headers:
                req.add_header('User-Agent', self.headers['User-Agent'])
            
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.getcode())
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
            self.send_error(502, "Bad Gateway")

def run_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    print(f"==================================================")
    print(f"🛡️  AEGIS EDGE SIMULATOR + API running on port {EDGE_PORT}")
    print(f"👉  API:    http://localhost:{EDGE_PORT}/api/stats")
    print(f"👉  Origin: {ORIGIN_URL}")
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
