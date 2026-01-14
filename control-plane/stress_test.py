"""
Aegis.net - Stress Test / DDoS Simulation
Testing protection system locally

IMPORTANT: This is only for testing on your own systems!
"""

import asyncio
import httpx
import time
from dataclasses import dataclass
from typing import List
import sys

# Fix encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

@dataclass
class TestResult:
    total_requests: int
    successful: int
    rate_limited: int
    errors: int
    duration: float
    rps: float

async def send_request(client: httpx.AsyncClient, url: str, request_id: int) -> dict:
    """Send one request"""
    try:
        start = time.time()
        response = await client.get(url)
        elapsed = time.time() - start
        
        return {
            "id": request_id,
            "status": response.status_code,
            "time": elapsed,
            "success": response.status_code == 200
        }
    except httpx.RequestError as e:
        return {
            "id": request_id,
            "status": 0,
            "time": 0,
            "error": str(e),
            "success": False
        }

async def run_attack_wave(
    target_url: str,
    requests_count: int,
    concurrent: int = 50
) -> TestResult:
    """
    Run wave of requests for testing
    """
    print(f"\n[ATTACK] Starting wave:")
    print(f"   Target: {target_url}")
    print(f"   Requests: {requests_count}")
    print(f"   Concurrent: {concurrent}")
    print("-" * 50)
    
    results: List[dict] = []
    start_time = time.time()
    
    semaphore = asyncio.Semaphore(concurrent)
    
    async def limited_request(client, url, req_id):
        async with semaphore:
            return await send_request(client, url, req_id)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            limited_request(client, target_url, i) 
            for i in range(requests_count)
        ]
        
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{requests_count} ({completed*100//requests_count}%)")
    
    duration = time.time() - start_time
    
    successful = sum(1 for r in results if r.get("status") == 200)
    rate_limited = sum(1 for r in results if r.get("status") == 429)
    errors = sum(1 for r in results if r.get("status") == 0 or r.get("status", 0) >= 500)
    
    return TestResult(
        total_requests=requests_count,
        successful=successful,
        rate_limited=rate_limited,
        errors=errors,
        duration=duration,
        rps=requests_count / duration
    )

def print_results(result: TestResult, wave_name: str):
    """Print wave results"""
    print(f"\n[RESULTS] {wave_name}")
    print("=" * 50)
    print(f"   Total requests:    {result.total_requests}")
    print(f"   [OK] Successful:   {result.successful} ({result.successful*100//result.total_requests}%)")
    print(f"   [BLOCKED]:         {result.rate_limited} ({result.rate_limited*100//result.total_requests}%)")
    print(f"   [ERROR]:           {result.errors}")
    print(f"   Time:              {result.duration:.2f}s")
    print(f"   RPS:               {result.rps:.0f} req/s")
    print("=" * 50)

async def main():
    print("""
    ============================================================
            AEGIS.NET - DDoS Protection Test
            Attack simulation for testing protection
    ============================================================
    """)
    
    base_url = "http://localhost:8000"
    
    print("[CHECK] Checking API availability...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   [OK] API is available!")
            else:
                print(f"   [WARN] API returned status: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] API unavailable: {e}")
        print("\n   Make sure API is running: python -m uvicorn api.main:app --reload")
        return
    
    # Wave 1: Light load
    print("\n" + "="*60)
    print("[WAVE 1] Light load (100 requests)")
    print("="*60)
    result1 = await run_attack_wave(
        f"{base_url}/health",
        requests_count=100,
        concurrent=10
    )
    print_results(result1, "Light load")
    
    await asyncio.sleep(2)
    
    # Wave 2: Medium load
    print("\n" + "="*60)
    print("[WAVE 2] Medium load (500 requests)")
    print("="*60)
    result2 = await run_attack_wave(
        f"{base_url}/health",
        requests_count=500,
        concurrent=50
    )
    print_results(result2, "Medium load")
    
    await asyncio.sleep(2)
    
    # Wave 3: High load (DDoS simulation)
    print("\n" + "="*60)
    print("[WAVE 3] High load - DDoS simulation (1000 requests)")
    print("="*60)
    result3 = await run_attack_wave(
        f"{base_url}/health",
        requests_count=1000,
        concurrent=100
    )
    print_results(result3, "DDoS simulation")
    
    # Final report
    print("\n")
    print("============================================================")
    print("                    FINAL REPORT                           ")
    print("============================================================")
    
    total_requests = result1.total_requests + result2.total_requests + result3.total_requests
    total_blocked = result1.rate_limited + result2.rate_limited + result3.rate_limited
    total_success = result1.successful + result2.successful + result3.successful
    
    print(f"""
    Total requests:     {total_requests}
    Successful:         {total_success}
    Blocked:            {total_blocked}
    
    Protection efficiency: {total_blocked*100//total_requests if total_requests > 0 else 0}%
    
    NOTE: For real protection you need to deploy Edge nodes
          with XDP filters and OpenResty WAF.
    """)

if __name__ == "__main__":
    print("\n[WARNING] This is a testing tool!")
    print("          Use only on your own systems.\n")
    
    asyncio.run(main())
