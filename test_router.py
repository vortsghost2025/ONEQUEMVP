import httpx
import json

client = httpx.Client(timeout=60)

print("=" * 60)
print("Testing /router/* Endpoints")
print("=" * 60)

# Test 1: Router route
print("\n1. POST /router/route")
try:
    r = client.post(
        "http://127.0.0.1:8081/router/route", json={"prompt": "Write a Python function"}
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Task type: {data.get('task_type')}")
        print(f"   Recommended: {data.get('recommended_model')}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Recommended models
print("\n2. GET /router/models/recommended")
try:
    r = client.get("http://127.0.0.1:8081/router/models/recommended")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Models count: {len(data.get('models', []))}")
        for m in data.get("models", [])[:3]:
            print(f"   - {m.get('name')} ({m.get('id')})")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: OpenAI models
print("\n3. GET /v1/models")
try:
    r = client.get("http://127.0.0.1:8081/v1/models")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Total models: {len(data.get('data', []))}")
except Exception as e:
    print(f"   Error: {e}")

# Test 4: OpenAI chat completions
print("\n4. POST /v1/chat/completions (model=auto)")
try:
    r = client.post(
        "http://127.0.0.1:8081/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "Say hello in 3 words"}],
            "max_tokens": 50,
        },
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        resp = r.json()
        print(f"   Model used: {resp.get('model')}")
        print(f"   Response: {resp['choices'][0]['message']['content']}")
except Exception as e:
    print(f"   Error: {e}")

# Test 5: Analyze prompt
print("\n5. GET /router/analyze")
try:
    r = client.get(
        "http://127.0.0.1:8081/router/analyze", params={"prompt": "Write a poem"}
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Task type: {data.get('task_type')}")
        print(f"   Reasoning: {data.get('reasoning', '')[:100]}")
except Exception as e:
    print(f"   Error: {e}")

# Test 6: Fallback generate
print("\n6. POST /router/generate/fallback")
try:
    r = client.post(
        "http://127.0.0.1:8081/router/generate/fallback", json={"prompt": "What is AI?"}
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        resp = r.json()
        print(f"   Success: {resp.get('success')}")
        print(f"   Model used: {resp.get('model_used')}")
        print(f"   Fallback attempts: {resp.get('fallback_attempts')}")
        print(f"   Response: {resp.get('response', '')[:80]}...")
except Exception as e:
    print(f"   Error: {e}")

# Test 7: Benchmark quick
print("\n7. GET /router/benchmark/quick")
try:
    r = client.get("http://127.0.0.1:8081/router/benchmark/quick")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        results = data.get("results", {})
        print(f"   Models benchmarked: {len(results)}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
