"""
Automated Benchmark for Top 10 Recommended Models
Tests speed, quality, and reliability of optimized model selection
"""

import httpx
import json
import time
from typing import List, Dict
from datetime import datetime

# Top 10 recommended models from benchmark tests
TOP_MODELS = [
    "meta/llama-4-maverick-17b-128e-instruct",  # Best overall
    "qwen/qwen2.5-coder-32b-instruct",  # Best coder
    "deepseek-ai/deepseek-r1-distill-llama-8b",  # Best reasoning
    "microsoft/phi-3.5-vision-instruct",  # Best vision + general
    "microsoft/phi-3-mini-4k-instruct",  # Fastest
    "meta/llama-3.1-70b-instruct",  # High quality fallback
    "meta/llama-3.1-405b-instruct",  # Highest quality (405B params)
    "mistralai/mistral-7b-instruct",  # Multilingual
    "qwen/qwen3-next-80b-a3b-instruct",  # Advanced tasks
    "google/gemma-3-27b-it",  # Balanced performance
]

# Test prompts by category
TEST_PROMPTS = {
    "general": "Explain quantum computing in one paragraph",
    "code": "Write a Python function to reverse a string",
    "reasoning": "If all roses are flowers and some flowers fade quickly, do some roses fade quickly?",
    "creative": "Write a haiku about artificial intelligence",
    "math": "What is 234 * 567 + 89?",
}

BASE_URL = "http://127.0.0.1:8081"


def benchmark_model(model_id: str, prompt: str, max_tokens: int = 100) -> Dict:
    """Test a single model and return performance metrics"""
    client = httpx.Client(timeout=120)

    start_time = time.time()

    try:
        response = client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )

        end_time = time.time()
        total_time = end_time - start_time

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "success": True,
                "model": model_id,
                "response_time": total_time,
                "content": content,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "error": None,
            }
        else:
            return {
                "success": False,
                "model": model_id,
                "response_time": total_time,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "model": model_id,
            "response_time": end_time - start_time,
            "error": str(e),
        }


def run_benchmark_suite():
    """Run comprehensive benchmark across all top models"""
    print("=" * 80)
    print("OneQueue Top 10 Model Benchmark Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {}
    client = httpx.Client(timeout=120)

    # Test each model with different prompt types
    for model_id in TOP_MODELS:
        print(f"\nTesting: {model_id}")
        model_results = {}

        for test_type, prompt in TEST_PROMPTS.items():
            print(f"  - Running {test_type} test...")
            result = benchmark_model(model_id, prompt)
            model_results[test_type] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.2f}s" if result["success"] else "N/A"
            print(f"    {status} {test_type}: {time_str}")

        results[model_id] = model_results

    # Generate summary report
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    # Calculate success rates and average times
    summary_data = []
    for model_id, model_results in results.items():
        successful = sum(1 for r in model_results.values() if r["success"])
        total = len(model_results)
        success_rate = (successful / total * 100) if total > 0 else 0

        avg_time = sum(
            r["response_time"] for r in model_results.values() if r["success"]
        ) / max(successful, 1)

        summary_data.append(
            {
                "model": model_id,
                "success_rate": success_rate,
                "avg_time": avg_time,
                "successful_tests": successful,
                "total_tests": total,
            }
        )

    # Sort by success rate, then by speed
    summary_data.sort(key=lambda x: (-x["success_rate"], x["avg_time"]))

    print("\nModel Performance Ranking:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Model':<50} {'Success':<10} {'Avg Time':<10}")
    print("-" * 80)

    for i, data in enumerate(summary_data, 1):
        model_short = (
            data["model"][:47] + "..." if len(data["model"]) > 50 else data["model"]
        )
        print(
            f"{i:<5} {model_short:<50} {data['success_rate']:>5.1f}%    {data['avg_time']:.2f}s"
        )

    # Save detailed results
    report = {
        "timestamp": datetime.now().isoformat(),
        "models_tested": len(TOP_MODELS),
        "test_prompts": len(TEST_PROMPTS),
        "results": results,
        "summary": summary_data,
    }

    report_file = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 Detailed report saved to: {report_file}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    try:
        print("Starting benchmark suite...")
        print(
            f"Testing {len(TOP_MODELS)} models with {len(TEST_PROMPTS)} test cases each"
        )
        print("=" * 80)

        report = run_benchmark_suite()

        print("\n✅ Benchmark complete!")
        print("\nTop 3 recommended models based on results:")
        for i, data in enumerate(report["summary"][:3], 1):
            print(
                f"  {i}. {data['model']} (Success: {data['success_rate']:.1f}%, Avg: {data['avg_time']:.2f}s)"
            )

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        print("Make sure the OneQueue server is running on http://127.0.0.1:8081")
