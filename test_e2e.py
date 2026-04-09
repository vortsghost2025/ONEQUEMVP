"""
Comprehensive End-to-End Test for OneQueue Optimized Models
Tests all 10 top recommended models with real API calls
"""

import httpx
import json
import time
from datetime import datetime

# Top 10 recommended models to test
TOP_MODELS = [
    "meta/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
    "microsoft/phi-3.5-vision-instruct",
    "microsoft/phi-3-mini-4k-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen3-next-80b-a3b-instruct",
    "google/gemma-3-27b-it",
]

# Test cases for different task types
TEST_CASES = [
    {
        "name": "General Knowledge",
        "prompt": "What is the capital of France? Answer in one sentence.",
        "expected_contains": "Paris",
        "type": "general",
    },
    {
        "name": "Code Generation",
        "prompt": "Write a Python function called 'add' that takes two numbers and returns their sum.",
        "expected_contains": "def add",
        "type": "code",
    },
    {
        "name": "Reasoning",
        "prompt": "If all roses are flowers and some flowers fade quickly, do some roses fade quickly? Answer yes or no with explanation.",
        "expected_contains": "yes",
        "type": "reasoning",
    },
    {
        "name": "Creative Writing",
        "prompt": "Write a haiku about artificial intelligence.",
        "expected_contains": "",
        "type": "creative",
    },
    {
        "name": "Math",
        "prompt": "What is 234 + 567? Give only the number.",
        "expected_contains": "801",
        "type": "math",
    },
]

BASE_URL = "http://127.0.0.1:8081"


def test_model(model_id: str, test_case: dict) -> dict:
    """Test a single model with a specific test case"""
    client = httpx.Client(timeout=120)

    start_time = time.time()

    try:
        response = client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": test_case["prompt"]},
                ],
                "max_tokens": 200,
                "temperature": 0.7,
            },
        )

        end_time = time.time()
        total_time = end_time - start_time

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"].lower()

            success = True
            if test_case["expected_contains"]:
                success = test_case["expected_contains"].lower() in content

            return {
                "success": success,
                "model": model_id,
                "test_name": test_case["name"],
                "response_time": total_time,
                "content": data["choices"][0]["message"]["content"][:200],
                "status_code": response.status_code,
                "error": None,
            }
        else:
            return {
                "success": False,
                "model": model_id,
                "test_name": test_case["name"],
                "response_time": total_time,
                "content": None,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "model": model_id,
            "test_name": test_case["name"],
            "response_time": end_time - start_time,
            "content": None,
            "status_code": None,
            "error": str(e),
        }


def run_full_test_suite():
    """Run comprehensive end-to-end test"""
    print("=" * 80)
    print("OneQueue End-to-End Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("")

    # First, check if server is running
    print("Step 1: Checking server health...")
    try:
        client = httpx.Client(timeout=10)
        r = client.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            print("  [OK] Server is running")
        else:
            print(f"  [WARN] Server returned status {r.status_code}")
    except Exception as e:
        print(f"  [FAIL] Server not responding: {e}")
        print("\nPlease ensure the OneQueue server is running on http://127.0.0.1:8081")
        return

    # Test smart router endpoint
    print("\nStep 2: Testing smart router endpoint...")
    try:
        r = client.post(
            f"{BASE_URL}/router/route", json={"prompt": "Write a Python function"}
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  [OK] Smart router working")
            print(f"       Task type: {data.get('task_type')}")
            print(f"       Recommended: {data.get('recommended_model')}")
        else:
            print(f"  [FAIL] Smart router returned {r.status_code}")
    except Exception as e:
        print(f"  [FAIL] Smart router error: {e}")

    # Test each model with a simple prompt
    print("\nStep 3: Testing all 10 top models...")
    print("-" * 80)

    results = []
    simple_prompt = "Say hello in exactly 3 words"

    for i, model_id in enumerate(TOP_MODELS, 1):
        print(f"\n{i}/10 Testing: {model_id}")

        result = test_model(
            model_id,
            {
                "name": "Quick Test",
                "prompt": simple_prompt,
                "expected_contains": "",
                "type": "general",
            },
        )

        results.append(result)

        if result["success"]:
            print(f"  [OK] Success - {result['response_time']:.2f}s")
            print(f"       Response: {result['content'][:100]}")
        else:
            print(f"  [FAIL] Failed - {result['error']}")

    # Test different task types with best model
    print("\n" + "=" * 80)
    print("Step 4: Testing different task types with Llama 4 Maverick...")
    print("-" * 80)

    best_model = "meta/llama-4-maverick-17b-128e-instruct"

    for test_case in TEST_CASES:
        print(f"\nTask: {test_case['name']}")
        result = test_model(best_model, test_case)

        if result["success"]:
            print(f"  [OK] Success - {result['response_time']:.2f}s")
            print(f"       Response: {result['content'][:150]}...")
        else:
            print(f"  [FAIL] Failed - {result['error']}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"\nModels tested: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {(successful / total * 100):.1f}%")

    if successful > 0:
        avg_time = sum(r["response_time"] for r in results if r["success"]) / successful
        print(f"Average response time: {avg_time:.2f}s")

    print("\n" + "=" * 80)
    print("[OK] End-to-end test complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_full_test_suite()
