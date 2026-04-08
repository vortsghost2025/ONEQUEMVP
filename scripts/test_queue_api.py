import sys, os

sys.path.append(os.path.abspath("."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# GET /queue/status
print("GET /queue/status ->", client.get("/queue/status").json())

# POST /queue/pause
print("POST /queue/pause ->", client.post("/queue/pause").json())

# GET again
print("GET after pause ->", client.get("/queue/status").json())

# POST /queue/resume
print("POST /queue/resume ->", client.post("/queue/resume").json())

# GET again
print("GET after resume ->", client.get("/queue/status").json())

# Ensure clear-failed works (no failed tasks yet)
print("POST /queue/clear-failed ->", client.post("/queue/clear-failed").json())
