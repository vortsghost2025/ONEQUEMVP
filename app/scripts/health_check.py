#!/usr/bin/env python3
"""
Health Check Script for OneQueue

Checks all service endpoints (/health, /ollama, /nvidia) and returns JSON status.
Designed to be callable by Uptime Kuma or similar monitoring tools.

Usage:
    python app/scripts/health_check.py

Environment variables:
    API_BASE_URL - Base URL of the OneQueue API (default: http://localhost:8000)
    OLLAMA_BASE_URL - Ollama base URL (default: http://localhost:11434)
    NVIDIA_API_KEY - NVIDIA API key for checking (optional)
    TIMEOUT_SECONDS - Request timeout in seconds (default: 5)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

import httpx


def get_config() -> Dict[str, Any]:
    """Get configuration from environment or defaults."""
    return {
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8000"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "nvidia_api_key": os.getenv("NVIDIA_API_KEY", ""),
        "timeout": float(os.getenv("TIMEOUT_SECONDS", "5")),
    }


async def check_api_health(base_url: str, timeout: float) -> Dict[str, Any]:
    """Check the main API /health endpoint."""
    result = {
        "endpoint": "/health",
        "status": "unknown",
        "latency_ms": 0,
        "error": None,
    }

    try:
        start = datetime.utcnow()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/health",
                timeout=timeout,
            )
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            result["latency_ms"] = int(elapsed)

            if response.status_code == 200:
                data = response.json()
                result["status"] = data.get("status", "healthy")
            else:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"

    except httpx.ConnectError:
        result["status"] = "offline"
        result["error"] = "Connection refused"
    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def check_ollama(ollama_url: str, timeout: float) -> Dict[str, Any]:
    """Check if Ollama is healthy."""
    result = {
        "endpoint": "/ollama",
        "status": "unknown",
        "latency_ms": 0,
        "models": [],
        "error": None,
    }

    try:
        start = datetime.utcnow()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ollama_url}/api/tags",
                timeout=timeout,
            )
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            result["latency_ms"] = int(elapsed)

            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                result["status"] = "healthy"
                result["models"] = models
            else:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"

    except httpx.ConnectError:
        result["status"] = "offline"
        result["error"] = "Connection refused"
    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def check_nvidia(nvidia_api_key: str, timeout: float) -> Dict[str, Any]:
    """Check if NVIDIA API is accessible."""
    result = {
        "endpoint": "/nvidia",
        "status": "unknown",
        "key_configured": False,
        "key_valid": False,
        "error": None,
    }

    nvidia_url = "https://integrate.api.nvidia.com/v1"

    if not nvidia_api_key:
        result["status"] = "missing_key"
        result["error"] = "NVIDIA_API_KEY not set"
        return result

    if not nvidia_api_key.startswith("nvapi-"):
        result["status"] = "invalid_key"
        result["error"] = "Invalid key format (should start with nvapi-)"
        return result

    result["key_configured"] = True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{nvidia_url}/models",
                headers={"Authorization": f"Bearer {nvidia_api_key}"},
                timeout=timeout,
            )

            if response.status_code == 200:
                result["status"] = "healthy"
                result["key_valid"] = True
            else:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"

    except httpx.ConnectError:
        result["status"] = "offline"
        result["error"] = "Connection refused"
    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def run_health_check() -> Dict[str, Any]:
    """Run all health checks and return combined result."""
    config = get_config()

    api_health = await check_api_health(config["api_base_url"], config["timeout"])
    ollama_health = await check_ollama(config["ollama_base_url"], config["timeout"])
    nvidia_health = await check_nvidia(
        config["nvidia_api_key"], config["timeout"]
    )

    overall_status = "healthy"
    if api_health["status"] != "healthy":
        overall_status = "degraded"
    if api_health["status"] == "offline" or (
        ollama_health["status"] == "offline" and nvidia_health["status"] in ["missing_key", "invalid_key"]
    ):
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "api": api_health,
        "ollama": ollama_health,
        "nvidia": nvidia_health,
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OneQueue Health Check Script"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output raw JSON (no formatting)"
    )
    parser.add_argument(
        "--exit-code", action="store_true", help="Exit with code based on health status"
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(run_health_check())

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))

        if args.exit_code:
            if result["status"] == "healthy":
                sys.exit(0)
            elif result["status"] == "degraded":
                sys.exit(1)
            else:
                sys.exit(2)

    except KeyboardInterrupt:
        sys.exit(3)
    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
        print(json.dumps(error_result))
        sys.exit(3)


if __name__ == "__main__":
    import asyncio

    main()