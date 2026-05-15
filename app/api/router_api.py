"""
API endpoints for Smart Router, Benchmark, and OpenAI Proxy
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

# ✅ Clean import - app/schemas/chat.py has ZERO project dependencies
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
)

logger = logging.getLogger("onequeue.router_api")

# Global service instances (initialized in main.py)
_smart_router = None
_model_benchmark = None
_openai_proxy = None


def get_smart_router():
    """Get smart router instance"""
    global _smart_router
    if _smart_router is None:
        from app.services.smart_router import SmartRouter

        _smart_router = SmartRouter()
    return _smart_router


def get_model_benchmark():
    """Get model benchmark instance"""
    global _model_benchmark
    if _model_benchmark is None:
        from app.services.model_benchmark import ModelBenchmark
        from app.services.nvidia_api import NvidiaAPI
        from app.services import ollama

        _model_benchmark = ModelBenchmark(nvidia_api=NvidiaAPI(), ollama_api=ollama)
    return _model_benchmark


def get_openai_proxy():
    """Get OpenAI proxy instance"""
    global _openai_proxy
    if _openai_proxy is None:
        from app.services.openai_proxy import OpenAIProxy

        _openai_proxy = OpenAIProxy()
    return _openai_proxy


# Request models
class RouteRequest(BaseModel):
    prompt: str
    preferred_model: Optional[str] = None
    prefer_speed: Optional[bool] = False
    prefer_quality: Optional[bool] = False
    require_local: Optional[bool] = False


class BenchmarkRequest(BaseModel):
    models: Optional[List[str]] = None
    tests: Optional[List[str]] = None
    suite: Optional[str] = None  # "speed_test", "quality_test", "code_test", etc.


# Create routers
router = APIRouter()


# Smart Router Endpoints
@router.post("/route")
async def route_task(request: RouteRequest):
    """
    Get smart model recommendation for a task

    Returns the best model for the task based on:
    - Task type detection
    - Model capabilities
    - Speed vs quality preferences
    """
    smart_router = get_smart_router()
    from app.services.smart_router import TaskType

    model_id, model_info = smart_router.select_model(
        prompt=request.prompt,
        preferred_model=request.preferred_model,
        prefer_speed=request.prefer_speed,
        prefer_quality=request.prefer_quality,
        require_local=request.require_local,
    )

    return {
        "recommended_model": model_id,
        "model_info": {
            "name": model_info.name,
            "provider": model_info.provider,
            "tier": model_info.tier,
            "context_length": model_info.context_length,
            "speed_score": model_info.speed_score,
            "quality_score": model_info.quality_score,
        },
        "task_type": smart_router.analyze_task(request.prompt).value,
        "fallback_chain": smart_router.get_fallback_chain(model_id),
    }


@router.get("/models/recommended")
async def get_recommended_models(task_type: Optional[str] = None, limit: int = 5):
    """Get recommended models, optionally filtered by task type"""
    smart_router = get_smart_router()
    from app.services.smart_router import TaskType

    task_enum = TaskType(task_type) if task_type else None
    models = smart_router.get_recommended_models(task_enum, limit)

    return {
        "task_type": task_type,
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "tier": m.tier,
                "quality_score": m.quality_score,
                "speed_score": m.speed_score,
            }
            for m in models
        ],
    }


@router.get("/models/{model_id}")
async def get_model_info(model_id: str):
    """Get detailed information about a specific model"""
    smart_router = get_smart_router()
    model_info = smart_router.get_model_info(model_id)

    if not model_info:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": model_info.id,
        "name": model_info.name,
        "provider": model_info.provider,
        "tier": model_info.tier,
        "category": model_info.category,
        "context_length": model_info.context_length,
        "specialty": [t.value for t in model_info.specialty],
        "speed_score": model_info.speed_score,
        "quality_score": model_info.quality_score,
        "cost_tier": model_info.cost_tier,
        "fallback_chain": smart_router.get_fallback_chain(model_id),
    }


@router.get("/analyze")
async def analyze_prompt(prompt: str):
    """Analyze a prompt to determine task type"""
    smart_router = get_smart_router()
    task_type = smart_router.analyze_task(prompt)
    models = smart_router.list_models_by_specialty(task_type)

    return {
        "task_type": task_type.value,
        "recommended_models": [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "quality_score": m.quality_score,
            }
            for m in models[:5]
        ],
    }


# Benchmark Endpoints
@router.post("/benchmark")
async def run_benchmark(request: BenchmarkRequest):
    """
    Run benchmarks on models

    Options:
    - models: List of model IDs to benchmark (default: key models)
    - tests: List of test names (default: general_simple, code_python, creative)
    - suite: Predefined test suite (speed_test, quality_test, code_test, comprehensive)
    """
    from app.services.model_benchmark import BENCHMARK_SUITE

    benchmark_system = get_model_benchmark()

    # Use suite if specified
    if request.suite:
        tests = BENCHMARK_SUITE.get(request.suite, None)
    else:
        tests = request.tests or ["general_simple", "code_python", "creative"]

    # Use default models if not specified
    models = request.models or [
        "meta/llama-4-maverick-17b-128e-instruct",
        "deepseek-ai/deepseek-v3.2",
        "llama3:latest",
    ]

    results = await benchmark_system.run_full_benchmark(models, tests)

    return {
        "status": "completed",
        "models_tested": len(models),
        "tests_run": len(tests),
        "results": results,
    }


@router.get("/benchmark/quick")
async def quick_benchmark():
    """Run quick benchmark on key models"""
    benchmark_system = get_model_benchmark()
    results = await benchmark_system.quick_comparison()

    return {"status": "completed", "results": results}


@router.get("/benchmark/results")
async def get_benchmark_results():
    """Get all benchmark results"""
    benchmark_system = get_model_benchmark()

    return {
        "total_results": len(benchmark_system.results),
        "results": [
            {
                "model_id": r.model_id,
                "test_name": r.test_name,
                "response_time_ms": r.response_time_ms,
                "tokens_per_second": r.tokens_per_second,
                "success": r.success,
            }
            for r in benchmark_system.results[-50:]  # Last 50 results
        ],
    }


@router.post("/benchmark/export")
async def export_benchmark():
    """Export benchmark results to JSON file"""
    benchmark_system = get_model_benchmark()
    benchmark_system.export_results("data/benchmark_results.json")

    return {"status": "exported", "filepath": "data/benchmark_results.json"}


@router.post("/benchmark/import")
async def import_benchmark():
    """Import benchmark results from JSON file"""
    benchmark_system = get_model_benchmark()
    benchmark_system.import_results("data/benchmark_results.json")

    return {"status": "imported", "total_results": len(benchmark_system.results)}


# OpenAI-Compatible Proxy Endpoints
@router.post("/v1/chat/completions")
async def openai_chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint

    Supports:
    - All OpenAI parameters
    - Model "auto" for smart routing
    - NVIDIA and Ollama models
    - Streaming (SSE)
    """
    openai_proxy = get_openai_proxy()

    if request.stream:
        return await openai_proxy.stream_chat_completion(request)
    else:
        return await openai_proxy.create_chat_completion(request)


@router.get("/v1/models")
async def openai_list_models():
    """OpenAI-compatible models list"""
    openai_proxy = get_openai_proxy()
    return openai_proxy.list_models()


@router.get("/v1/models/{model_id}")
async def openai_get_model(model_id: str):
    """OpenAI-compatible model info"""
    openai_proxy = get_openai_proxy()
    return openai_proxy.get_model(model_id)


# Fallback Chain Endpoints
@router.get("/fallback/{model_id}")
async def get_fallback_chain(model_id: str):
    """Get fallback chain for a model"""
    smart_router = get_smart_router()
    chain = smart_router.get_fallback_chain(model_id)

    return {
        "primary_model": model_id,
        "fallback_chain": chain,
        "chain_info": [
            {
                "position": i + 1,
                "model_id": m,
                "model_name": smart_router.get_model_info(m).name
                if smart_router.get_model_info(m)
                else m,
            }
            for i, m in enumerate(chain)
        ],
    }


@router.post("/generate/fallback")
async def generate_with_fallback(request: RouteRequest):
    """Generate with automatic fallback on failure"""
    smart_router = get_smart_router()

    model_id, _ = smart_router.select_model(request.prompt, request.preferred_model)
    fallback_chain = smart_router.get_fallback_chain(model_id)

    errors = []

    for attempt_model in fallback_chain:
        try:
            if smart_router._is_nvidia_model(attempt_model):
                from app.services.nvidia_api import NvidiaAPI

                nvidia_api = NvidiaAPI()
                response = await nvidia_api.generate(
                    model=attempt_model, prompt=request.prompt, max_tokens=2048
                )
                content = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            else:
                from app.services import ollama

                content = await ollama.generate(
                    prompt=request.prompt, model=attempt_model, timeout=120
                )

            return {
                "success": True,
                "model_used": attempt_model,
                "response": content,
                "fallback_attempts": len(errors),
                "errors": errors if errors else None,
            }

        except Exception as e:
            errors.append({"model": attempt_model, "error": str(e)})
            logger.warning(f"Fallback: {attempt_model} failed, trying next...")
            continue

    return {
        "success": False,
        "error": "All models in fallback chain failed",
        "errors": errors,
    }
