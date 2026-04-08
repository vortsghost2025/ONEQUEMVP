import sys, os

sys.path.append(os.path.abspath("."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Trigger startup events by creating client (FastAPI does it automatically)
response = client.get("/docs")
print("Docs status", response.status_code)
# Get Settings
resp = client.get("/settings")
print("Settings response", resp.status_code, resp.json())
# Create a task
resp = client.post("/tasks", json={"title": "Test task", "prompt": "Hello"})
print("Create task", resp.status_code, resp.json())
