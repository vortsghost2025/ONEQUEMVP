"""Simple stress test for OneQueue"""

import httpx
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:8081"
client = httpx.Client(timeout=300)

print("=" * 70)
print("ONEQUEUE STRESS TEST")
print("=" * 70)

# Test 1: Health
print("\n[1] Server Health")
r = client.get(f"{BASE_URL}/health")
print(f"Status: {r.status_code} - {'OK' if r.status_code == 200 else 'FAIL'}")

# Test 2: Single task
print("\n[2] Single Task Test")
r = client.post(
    f"{BASE_URL}/tasks",
    json={
        "title": "Test 1",
        "prompt": "Say hi",
        "model": "microsoft/phi-3-mini-4k-instruct",
        "timeout_seconds": 60,
    },
)
print(f"Create task: {r.status_code}")
if r.status_code in [200, 201]:
    task_id = r.json().get("id")
    print(f"Task ID: {task_id}")

    # Wait for completion
    for i in range(30):
        time.sleep(1)
        r2 = client.get(f"{BASE_URL}/tasks/{task_id}")
        if r2.status_code == 200:
            task = r2.json()
            if task.get("status") == "completed":
                print(f"Completed in {i + 1}s")
                print(f"Output: {task.get('output_text', '')[:50]}")
                break
            elif task.get("status") == "failed":
                print(f"Failed: {task.get('error_text')}")
                break

# Test 3: Ramp test
print("\n[3] Bulk Submission Ramp Test")
for count in [5, 10, 20]:
    print(f"\n  Submitting {count} tasks...")

    def create_task(n):
        r = client.post(
            f"{BASE_URL}/tasks",
            json={
                "title": f"Bulk {n}",
                "prompt": f"Count {n}",
                "model": "microsoft/phi-3-mini-4k-instruct",
                "timeout_seconds": 120,
            },
        )
        return r.status_code in [200, 201]

    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(create_task, range(count)))

    success = sum(results)
    print(f"  Success: {success}/{count}")

    # Check queue
    r = client.get(f"{BASE_URL}/queue/status")
    if r.status_code == 200:
        q = r.json()
        print(
            f"  Queue: {q.get('pending_count')} pending, {q.get('running_count')} running"
        )

    if success < count:
        print(f"  FAILED at {count} concurrent tasks")
        break

    time.sleep(10)  # Wait for tasks to complete

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
