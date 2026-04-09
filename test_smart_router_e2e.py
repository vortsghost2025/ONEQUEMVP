"""
Test the smart router's model selection with actual NVIDIA API calls
"""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8081"

# Test different task types
test_prompts = [
    ("General", "Explain what AI is in one sentence"),
    ("Code", "Write a Python function to calculate factorial"),
    (
        "Reasoning",
        "If A is greater than B, and B is greater than C, is A greater than C?",
    ),
    ("Math", "What is 123 * 456 + 789?"),
    ("Creative", "Write a short poem about technology"),
]

# Models to test
models_to_test = [
    "meta/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
    "microsoft/phi-3.5-vision-instruct",
    "microsoft/phi-3-mini-4k-instruct",
    "meta/llama-3.1-70b-instruct",
    "qwen/qwen3-next-80b-a3b-instruct",
]

print("=" * 80)
print("Smart Router Model Testing")
print("=" * 80)

client = httpx.Client(timeout=120)

# Test 1: Check smart router recommendations
print("\n1. Testing Smart Router Recommendations")
print("-" * 80)

for task_name, prompt in test_prompts:
    try:
        response = client.post(f"{BASE_URL}/router/route", json={"prompt": prompt})

        if response.status_code == 200:
            data = response.json()
            model = data.get("recommended_model", "Unknown")
            task_type = data.get("task_type", "Unknown")
            print(f"  {task_name:10} -> {task_type:15} -> {model}")
        else:
            print(f"  {task_name:10} -> ERROR: {response.status_code}")
    except Exception as e:
        print(f"  {task_name:10} -> EXCEPTION: {e}")

# Test 2: Test each model with its specialty
print("\n2. Testing Individual Models")
print("-" * 80)

for model_id in models_to_test:
    print(f"\nTesting: {model_id}")

    # Simple test prompt
    try:
        start = time.time()
        response = client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": "Say 'test successful' in exactly 3 words",
                    }
                ],
                "max_tokens": 20,
            },
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"  [OK] {elapsed:.2f}s - {content[:100]}")
        else:
            print(f"  [FAIL] HTTP {response.status_code}")
    except Exception as e:
        print(f"  [FAIL] {e}")

# Test 3: Test fallback mechanism
print("\n3. Testing Fallback Mechanism")
print("-" * 80)

try:
    response = client.post(
        f"{BASE_URL}/router/generate/fallback", json={"prompt": "What is 2+2?"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"  Success: {data.get('success')}")
        print(f"  Model used: {data.get('model_used')}")
        print(f"  Fallback attempts: {data.get('fallback_attempts', 0)}")
        print(f"  Response: {data.get('response', '')[:100]}")
    else:
        print(f"  ERROR: {response.status_code}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

print("\n" + "=" * 80)
print("[OK] Smart router testing complete!")
print("=" * 80)
