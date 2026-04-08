import sys, os

sys.path.append(os.path.abspath("."))

import json
import httpx
from app.config import settings

url = f"{settings.OLLAMA_BASE_URL}"  # not needed but just to load config
# Actually we'll target the FastAPI server on 127.0.0.1:8080
api_url = "http://127.0.0.1:8080/settings"
payload = {"max_cpu_percent": 85.0, "queue_paused": True}

resp = httpx.patch(api_url, json=payload)
print("Status", resp.status_code)
print("Response", resp.json())
