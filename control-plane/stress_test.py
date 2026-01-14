"""
Aegis.net - Stress Test / DDoS Simulation
Testing protection system locally

IMPORTANT: This is only for testing on your own systems!
"""

import time
import urllib.request
import urllib.error
import threading
import concurrent.futures
import sys
import random
from dataclasses import dataclass

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

@dataclass
class TestResult:
    total_requests: int
    successful: int
    rate_limited: int
    errors: int
    duration: float
    rps: float

def send_request(url: str, request_id: int, headers: dict = None) -> dict:
    """Send one request using standard library"""
    if headers is None:
        headers = {}
    
    # Ensure User-Agent is set
    if "User-Agent" not in headers:
        headers["User-Agent"] = f"AegisStressTest/1.0 (Req-{request_id})"

    try:
        req = urllib.request.Request(url, headers=headers)
        start = time.time()
        with urllib.request.urlopen(req, timeout=5) as response:
            elapsed = time.time() - start
            return {
                "id": request_id,
                "status": response.getcode(),
                "time": elapsed,
                "success": True
            }
    except urllib.error.HTTPError as e:
        return {
            "id": request_id,
            "status": e.code,
            "time": 0,
            "success": False, # Technically false for counting "OK" responses
            "error_msg": str(e)
        }
    except Exception as e:
        return {
            "id": request_id,
            "status": 0,
            "time": 0,
            "success": False,
            "error_msg": str(e)
        }

def run_attack_wave(
    target_url: str,
    requests_count: int,
    concurrent_threads: int = 50,
    headers_factory = None
) -> TestResult:
    """
    Run wave of requests using ThreadPoolExecutor
    """
    print(f"\n[ATTACK] Starting wave:")
    print(f"   Target: {target_url}")
    print(f"   Requests: {requests_count}")
    print(f"   Threads: {concurrent_threads}")
    print("-" * 50)
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        futures = []
        for i in range(requests_count):
            h = headers_factory(i) if headers_factory else {}
            futures.append(executor.submit(send_request, target_url, i, h))

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed % 50 == 0:
                 print(f"   Progress: {completed}/{requests_count} ({completed*100//requests_count}%)")

    duration = time.time() - start_time
    
    successful = sum(1 for r in results if r.get("status") == 200)
    rate_limited = sum(1 for r in results if r.get("status") == 429 or r.get("status") == 503)
    errors = sum(1 for r in results if r.get("status") == 0 or r.get("status", 0) >= 500)
    
    return TestResult(
        total_requests=requests_count,
        successful=successful,
        rate_limited=rate_limited,
        errors=errors,
        duration=duration,
        rps=requests_count / duration if duration > 0 else 0
    )

def print_results(result: TestResult, wave_name: str):
    """Print wave results"""
    print(f"\n[RESULTS] {wave_name}")
    print("=" * 50)
    print(f"   Total requests:    {result.total_requests}")
    print(f"   [OK] Successful:   {result.successful} ({result.successful*100//result.total_requests if result.total_requests else 0}%)")
    print(f"   [BLOCKED]:         {result.rate_limited} ({result.rate_limited*100//result.total_requests if result.total_requests else 0}%)")
    print(f"   [ERROR]:           {result.errors}")
    print(f"   Time:              {result.duration:.2f}s")
    print(f"   RPS:               {result.rps:.0f} req/s")
    print("=" * 50)

def main():
    print("""
    ============================================================
            AEGIS.NET - DDoS Protection Test
            (Standalone Version)
    ============================================================
    """)
    
    # Target Mock Edge Node
    base_url = "http://localhost:8080"
    
    print("[CHECK] Checking API availability...")
    try:
        # Simple check
        req = urllib.request.Request(base_url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.getcode() == 200:
                print("   [OK] Target is available!")
    except Exception as e:
        print(f"   [ERROR] Target unavailable: {e}")
        print("\n   Make sure 'start_demo.ps1' is running!")
        return
    
    # Wave 1: Light load
    print("\n" + "="*60)
    print("[WAVE 1] Light load (50 requests)")
    print("="*60)
    result1 = run_attack_wave(
        base_url,
        requests_count=50,
        concurrent_threads=5
    )
    print_results(result1, "Light load")
    
    time.sleep(2)
    
    # Wave 2: DDoS Simulation
    print("\n" + "="*60)
    print("[WAVE 2] DDoS Simulation (500 requests)")
    print("="*60)
    result2 = run_attack_wave(
        base_url,
        requests_count=500,
        concurrent_threads=50
    )
    print_results(result2, "DDoS Load")
    
    time.sleep(2)

    # Wave 3: Botnet (Random IPs)
    print("\n" + "="*60)
    print("[WAVE 3] Botnet IP Spoofing (1000 requests)")
    print("="*60)
    
    def botnet_headers(i):
        spoofed_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        return {"X-Forwarded-For": spoofed_ip, "User-Agent": f"BotnetNode/{i}"}

    result3 = run_attack_wave(
        base_url,
        requests_count=1000,
        concurrent_threads=100,
        headers_factory=botnet_headers
    )
    print_results(result3, "Botnet Simulation")

    print("\n\n[TEST COMPLETE] Check your browser window to see if you were blocked!")

if __name__ == "__main__":
    main()
