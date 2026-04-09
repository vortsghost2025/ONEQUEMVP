import httpx
import json

print("Testing OpenAI-compatible endpoint...")
r = httpx.post(
    "http://127.0.0.1:8081/v1/chat/completions",
    json={
        "model": "auto",
        "messages": [{"role": "user", "content": "Say hi in 3 words"}],
        "max_tokens": 20,
    },
    timeout=60,
)

print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Model: {data.get('model')}")
    print(f"Response: {data['choices'][0]['message']['content']}")
else:
    print(f"Error: {r.text[:300]}")
