import requests
import time
from concurrent.futures import ThreadPoolExecutor

DOMAIN = "nginx-test.local"
URL = "http://77.221.153.207"
HEADERS = {"Host": DOMAIN}
TOTAL_REQUESTS = 50
CONCURRENCY = 3

def send_request(i):
    try:
        start = time.time()
        resp = requests.get(URL, headers=HEADERS, timeout=5)
        elapsed = time.time() - start
        
        status = resp.status_code
        if status == 503:
            return "BLOCKED"
        elif status == 200:
            return "OK"
        else:
            return f"ERR_{status}"
    except Exception as e:
        print(f"Request {i} failed: {type(e).__name__}: {e}")
        return "FAIL"

def run_test():
    print(f"Starting stress test for {DOMAIN} on {URL}")
    print(f"Requests: {TOTAL_REQUESTS}, Threads: {CONCURRENCY}")
    
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        for i in range(TOTAL_REQUESTS):
            results.append(executor.submit(send_request, i))
            
    # Process results
    counts = {"OK": 0, "BLOCKED": 0, "FAIL": 0}
    for future in results:
        res = future.result()
        if res == "OK": counts["OK"] += 1
        elif res == "BLOCKED": counts["BLOCKED"] += 1
        else: counts["FAIL"] += 1
        
    print("\n--- Test Results ---")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"✅ Passed: {counts['OK']}")
    print(f"🛡️ Blocked (503): {counts['BLOCKED']}")
    print(f"❌ Failed: {counts['FAIL']}")

if __name__ == "__main__":
    run_test()
