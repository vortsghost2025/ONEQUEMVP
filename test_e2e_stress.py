"""
OneQueue End-to-End Stress Test
Tests server health, task submission, bulk operations, and resource monitoring
"""

import httpx
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE_URL = "http://127.0.0.1:8081"


def main():
    print("=" * 70)
    print("ONEQUEUE END-TO-END STRESS TEST")
    print("=" * 70)
    print()

    client = httpx.Client(timeout=300)

    # Test 1: Server Health
    print("TEST 1: Server Health Check")
    print("-" * 70)
    try:
        r = client.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            print(f"  [PASS] Server healthy (status: {r.status_code})")
        else:
            print(f"  [FAIL] Server returned {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"  [FAIL] Cannot connect: {e}")
        sys.exit(1)

    # Test 2: Smart Router
    print("\nTEST 2: Smart Router Functionality")
    print("-" * 70)
    try:
        r = client.post(
            f"{BASE_URL}/router/route", json={"prompt": "Write a Python function"}
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  [PASS] Smart router working")
            print(f"       Task type: {data.get('task_type')}")
            print(f"       Model: {data.get('recommended_model')}")
        else:
            print(f"  [FAIL] Router returned {r.status_code}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Test 3: Queue Status
    print("\nTEST 3: Queue Status")
    print("-" * 70)
    try:
        r = client.get(f"{BASE_URL}/queue/status")
        if r.status_code == 200:
            data = r.json()
            print(f"  [PASS] Queue status retrieved")
            print(f"       Paused: {data.get('queue_paused')}")
            print(f"       Pending: {data.get('pending_count')}")
            print(f"       Running: {data.get('running_count')}")
        else:
            print(f"  [FAIL] Queue status returned {r.status_code}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Test 4: Submit Single Task
    print("\nTEST 4: Submit Single Task")
    print("-" * 70)
    task_id = None
    try:
        r = client.post(
            f"{BASE_URL}/tasks",
            json={
                "title": "E2E Test Task",
                "prompt": "Say hello in 3 words",
                "model": "meta/llama-4-maverick-17b-128e-instruct",
                "timeout_seconds": 60,
            },
        )
        if r.status_code == 200:
            data = r.json()
            task_id = data.get("id")
            print(f"  [PASS] Task created: {task_id}")
        else:
            print(f"  [FAIL] Task creation returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Wait for task completion
    if task_id:
        print("\nTEST 5: Task Completion")
        print("-" * 70)
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            r = client.get(f"{BASE_URL}/tasks/{task_id}")
            if r.status_code == 200:
                data = r.json()
                status = data.get("status")
                if status == "completed":
                    print(f"  [PASS] Task completed in {i + 1}s")
                    output = data.get("output_text", "")
                    print(f"       Output: {output[:100]}...")
                    break
                elif status == "failed":
                    print(f"  [FAIL] Task failed: {data.get('error_text')}")
                    break
            elif i == 29:
                print(f"  [FAIL] Task timeout after 30s")

        # Get task runs
        r = client.get(f"{BASE_URL}/tasks/{task_id}/runs")
        if r.status_code == 200:
            runs = r.json()
            print(f"  [INFO] Task had {len(runs)} run(s)")
            if runs:
                run = runs[0]
                print(f"       CPU: {run.get('cpu_percent')}%")
                print(f"       RAM: {run.get('ram_percent')}%")
                print(f"       Duration: {run.get('duration_ms')}ms")

    # Test 6: Bulk Task Submission (Ramp Up)
    print("\nTEST 6: Bulk Task Submission (Ramp Test)")
    print("-" * 70)

    def submit_task(task_num):
        try:
            r = client.post(
                f"{BASE_URL}/tasks",
                json={
                    "title": f"Ramp Test Task {task_num}",
                    "prompt": f"Count to 10: {task_num}",
                    "model": "microsoft/phi-3-mini-4k-instruct",
                    "timeout_seconds": 120,
                },
            )
            return r.status_code == 200
        except:
            return False

    ramp_levels = [5, 10, 20, 50]
    max_concurrent_success = 0

    for concurrent_tasks in ramp_levels:
        print(f"\n  Submitting {concurrent_tasks} tasks...")
        start = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_tasks) as executor:
            futures = [executor.submit(submit_task, i) for i in range(concurrent_tasks)]
            results = [f.result() for f in futures]

        elapsed = time.time() - start
        success_count = sum(results)
        print(f"    Submitted: {success_count}/{concurrent_tasks} in {elapsed:.2f}s")

        if success_count < concurrent_tasks:
            print(f"    [WARN] Some tasks failed at {concurrent_tasks} concurrent")
            break

        max_concurrent_success = concurrent_tasks

        # Wait for completion
        time.sleep(5)  # Give tasks time to process
        r = client.get(f"{BASE_URL}/queue/status")
        if r.status_code == 200:
            data = r.json()
            pending = data.get("pending_count", 0)
            running = data.get("running_count", 0)
            print(f"    Queue: {pending} pending, {running} running")

    # Test 7: Resource Monitoring During Load
    print("\nTEST 7: Resource Monitoring During Load")
    print("-" * 70)
    r = client.get(f"{BASE_URL}/queue/status")
    if r.status_code == 200:
        data = r.json()
        print(f"  Queue paused: {data.get('queue_paused')}")
        print(f"  Pending: {data.get('pending_count')}")
        print(f"  Running: {data.get('running_count')}")

    print("\n" + "=" * 70)
    print("E2E TEST COMPLETE")
    print(f"Maximum concurrent tasks successful: {max_concurrent_success}")
    print("=" * 70)


if __name__ == "__main__":
    main()
