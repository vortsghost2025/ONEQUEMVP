"""Simple server runner for testing"""

import sys

sys.path.insert(0, "S:/TAKE10")

from app.main import app
import uvicorn

print("Starting OneQueue server on http://127.0.0.1:8081")
uvicorn.run(app, host="127.0.0.1", port=8081, log_level="warning")
