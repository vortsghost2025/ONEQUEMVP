"""
Auto-Benchmark System for Model Performance
Tests models with standardized prompts and measures quality/speed
"""

import asyncio
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger("onequeue.benchmark")


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test"""

    model_id: str
    model_name: str
    test_name: str
    prompt: str
    response: str
    response_time_ms: float
    tokens_generated: int
    tokens_per_second: float
    quality_score: Optional[float] = None  # 1-10 rating
    success: bool = True
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class ModelBenchmark:
    """Automated benchmark system for model comparison"""

    def __init__(self, nvidia_api, ollama_api):
        self.nvidia_api = nvidia_api
        self.ollama_api = ollama_api
        self.results: List[BenchmarkResult] = []

        # Standard test prompts for different task types
        self.test_prompts = {
            "general_simple": "What is 2+2? Answer in one word.",
            "general_moderate": "Explain quantum computing in 3 sentences.",
            "code_python": "Write a Python function to reverse a string.",
            "code_javascript": "Write a JavaScript function to check if a number is prime.",
            "math_basic": "Solve: 15 * 23 + 48",
            "math_complex": "Explain the difference between differential and integral calculus.",
            "reasoning": "If all roses are flowers, and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning.",
            "creative": "Write a haiku about artificial intelligence.",
            "analysis": "Compare and contrast REST and GraphQL APIs in 5 bullet points.",
            "long_context": "Summarize the key principles of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Include examples for each.",
        }

    async def benchmark_model(
        self, model_id: str, test_name: str, prompt: str, timeout: int = 60
    ) -> BenchmarkResult:
        """Run a single benchmark test on a model"""

        start_time = time.time()

        try:
            # Determine which API to use
            if (
                model_id.startswith("meta/")
                or model_id.startswith("deepseek-ai/")
                or model_id.startswith("nvidia/")
                or model_id.startswith("qwen/")
                or model_id.startswith("google/")
                or model_id.startswith("microsoft/")
                or model_id.startswith("mistralai/")
            ):
                # NVIDIA API
                response_text = await self.nvidia_api.generate(
                    model=model_id, prompt=prompt, max_tokens=500
                )
                response_text = (
                    response_text.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            else:
                # Ollama API
                response_text = await self.ollama_api.generate(
                    prompt=prompt, model=model_id, timeout=timeout
                )

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # Estimate tokens
            tokens_generated = len(response_text) // 4  # Rough estimate
            tokens_per_second = (
                (tokens_generated / (response_time_ms / 1000))
                if response_time_ms > 0
                else 0
            )

            result = BenchmarkResult(
                model_id=model_id,
                model_name=model_id.split("/")[-1] if "/" in model_id else model_id,
                test_name=test_name,
                prompt=prompt,
                response=response_text[:1000],  # Truncate for storage
                response_time_ms=response_time_ms,
                tokens_generated=tokens_generated,
                tokens_per_second=tokens_per_second,
                success=True,
            )

            logger.info(
                f"✅ Benchmark {test_name} on {model_id}: {response_time_ms:.0f}ms, {tokens_per_second:.1f} tok/s"
            )

        except Exception as e:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            result = BenchmarkResult(
                model_id=model_id,
                model_name=model_id.split("/")[-1] if "/" in model_id else model_id,
                test_name=test_name,
                prompt=prompt,
                response="",
                response_time_ms=response_time_ms,
                tokens_generated=0,
                tokens_per_second=0,
                success=False,
                error=str(e),
            )

            logger.error(f"❌ Benchmark {test_name} on {model_id} failed: {e}")

        self.results.append(result)
        return result

    async def run_full_benchmark(
        self, models: List[str], tests: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """Run comprehensive benchmarks on multiple models"""

        if tests is None:
            tests = ["general_simple", "code_python", "creative"]

        logger.info(
            f"🏁 Starting full benchmark for {len(models)} models with {len(tests)} tests"
        )

        benchmark_summary = {}

        for model_id in models:
            logger.info(f"\n📊 Benchmarking: {model_id}")
            benchmark_summary[model_id] = {
                "model_id": model_id,
                "tests": [],
                "avg_response_time_ms": 0,
                "avg_tokens_per_second": 0,
                "success_rate": 0,
            }

            successful_tests = 0
            total_response_time = 0
            total_tokens_per_second = 0

            for test_name in tests:
                prompt = self.test_prompts.get(
                    test_name, self.test_prompts["general_simple"]
                )

                result = await self.benchmark_model(
                    model_id=model_id, test_name=test_name, prompt=prompt
                )

                benchmark_summary[model_id]["tests"].append(asdict(result))

                if result.success:
                    successful_tests += 1
                    total_response_time += result.response_time_ms
                    total_tokens_per_second += result.tokens_per_second

            # Calculate averages
            num_tests = len(tests)
            benchmark_summary[model_id]["success_rate"] = (
                successful_tests / num_tests
            ) * 100

            if successful_tests > 0:
                benchmark_summary[model_id]["avg_response_time_ms"] = (
                    total_response_time / successful_tests
                )
                benchmark_summary[model_id]["avg_tokens_per_second"] = (
                    total_tokens_per_second / successful_tests
                )

            logger.info(
                f"   Success rate: {benchmark_summary[model_id]['success_rate']:.0f}%"
            )
            logger.info(
                f"   Avg speed: {benchmark_summary[model_id]['avg_tokens_per_second']:.1f} tok/s"
            )

        return benchmark_summary

    async def quick_comparison(self) -> Dict:
        """Quick comparison of key models"""

        key_models = [
            "meta/llama-4-maverick-17b-128e-instruct",
            "deepseek-ai/deepseek-v3.2",
            "qwen/qwen3-coder-480b-a35b-instruct",
            "llama3:latest",
        ]

        quick_tests = ["general_simple", "code_python"]

        return await self.run_full_benchmark(key_models, quick_tests)

    def get_best_model_for_task(self, task_type: str) -> Optional[str]:
        """Get the best performing model for a task type based on benchmarks"""

        if not self.results:
            return None

        # Filter results by task type
        relevant_results = [
            r for r in self.results if task_type in r.test_name and r.success
        ]

        if not relevant_results:
            return None

        # Sort by speed (tokens per second)
        relevant_results.sort(key=lambda r: r.tokens_per_second, reverse=True)

        return relevant_results[0].model_id

    def export_results(self, filepath: str = "benchmark_results.json"):
        """Export benchmark results to JSON"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "results": [asdict(r) for r in self.results],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"📤 Exported {len(self.results)} benchmark results to {filepath}")

    def import_results(self, filepath: str = "benchmark_results.json"):
        """Import benchmark results from JSON"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            for result_data in data.get("results", []):
                result = BenchmarkResult(**result_data)
                self.results.append(result)

            logger.info(
                f"📥 Imported {len(data.get('results', []))} benchmark results from {filepath}"
            )

        except FileNotFoundError:
            logger.warning(f"No benchmark file found at {filepath}")


# Benchmark test suite
BENCHMARK_SUITE = {
    "speed_test": ["general_simple", "general_moderate"],
    "quality_test": ["reasoning", "analysis"],
    "code_test": ["code_python", "code_javascript"],
    "creative_test": ["creative", "analysis"],
    "comprehensive": None,  # All tests
}
