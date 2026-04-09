import httpx

client = httpx.Client(timeout=30)

# Check what status code task creation returns
print("Testing task creation status code...")
r = client.post(
    "http://127.0.0.1:8081/tasks",
    json={
        "title": "Test",
        "prompt": "Hello",
        "model": "microsoft/phi-3-mini-4k-instruct",
        "timeout_seconds": 60,
    },
)
print(f"Status code: {r.status_code}")
print(f"Response: {r.text[:500]}")

# Check existing tasks
r2 = client.get("http://127.0.0.1:8081/tasks")
print(f"\nTasks endpoint status: {r2.status_code}")
if r2.status_code == 200:
    tasks = r2.json()
    print(f"Task count: {len(tasks)}")
    if tasks:
        first_task = tasks[0]
        print(f"First task status: {first_task.get('status')}")
        print(f"First task title: {first_task.get('title')}")
