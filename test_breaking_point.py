"""Find the breaking point with increasing load"""

import httpx
import time
from concurrent.futures import ThreadPoolExecutor

client = httpx.Client(timeout=300)

print("RAMPING UP LOAD TEST")
print("=" * 70)

for count in [30, 50, 100, 200]:
    print(f"\nAttempting {count} concurrent tasks...")

    def create_task(n):
        try:
            r = client.post(
                "http://127.0.0.1:8081/tasks",
                json={
                    "title": f"Load {n}",
                    "prompt": f"Count {n}",
                    "model": "microsoft/phi-3-mini-4k-instruct",
                    "timeout_seconds": 300,
                },
            )
            return r.status_code in [200, 201]
        except Exception as e:
            print(f"Error: {e}")
            return False

    start = time.time()
    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(create_task, range(count)))
    elapsed = time.time() - start

    success = sum(results)
    print(f"Submitted: {success}/{count} in {elapsed:.2f}s")

    # Check queue status
    r = client.get("http://127.0.0.1:8081/queue/status")
    if r.status_code == 200:
        q = r.json()
        print(
            f"Queue: {q.get('pending_count')} pending, {q.get('running_count')} running"
        )

    # Check if server is still responsive
    r2 = client.get("http://127.0.0.1:8081/health")
    print(f"Health: {r2.status_code}")

    if success < count:
        print(f"\n*** BREAKING POINT REACHED AT {count} ***")
        break

    time.sleep(15)

print("\nTest complete")
