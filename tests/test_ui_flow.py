import time
import httpx

BASE = "http://127.0.0.1:8081"

def test_ui_end_to_end():
    # Verify UI is reachable
    r = httpx.get(f"{BASE}/ui")
    assert r.status_code == 200
    assert "OneQueue Dashboard" in r.text

    # Fetch model list
    r = httpx.get(f"{BASE}/v1/models")
    assert r.status_code == 200
    models = r.json().get("data", [])
    assert isinstance(models, list) and len(models) > 0
    model_id = models[0]["id"] if isinstance(models[0], dict) else models[0]

    # Create a task
    payload = {"model": model_id, "prompt": "Say hello"}
    r = httpx.post(f"{BASE}/tasks", json=payload)
    assert r.status_code == 200
    task = r.json()
    task_id = task["id"]

    # Poll until completed (max 30s)
    deadline = time.time() + 30
    while time.time() < deadline:
        r = httpx.get(f"{BASE}/tasks")
        tasks = r.json()
        matching = [t for t in tasks if t["id"] == task_id]
        if matching and matching[0]["status"].lower() == "completed":
            assert matching[0]["result"] is not None
            return
        time.sleep(2)
    assert False, "Task did not complete within timeout"
