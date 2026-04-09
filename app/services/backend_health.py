"""
Backend Health Checker - Prevents running tasks when backends are down
Critical safety check before task execution
"""

import asyncio
import logging
import httpx
from typing import Dict, List
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger("onequeue.backend_health")


class BackendHealthChecker:
    """
    Checks health of inference backends before task execution.

    Prevents zombie workers from running tasks when:
    - Ollama is down
    - NVIDIA API is unreachable
    - Both backends are unavailable
    """

    def __init__(self):
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.nvidia_url = "https://integrate.api.nvidia.com/v1"
        self._cache: Dict[str, dict] = {}
        self._cache_ttl = timedelta(seconds=30)

    async def check_ollama(self, use_cache: bool = True) -> Dict:
        """
        Check if Ollama is responding.

        Returns:
            {
                "status": "healthy" | "offline" | "error",
                "latency_ms": int,
                "models": List[str] (if healthy),
                "error": str (if error)
            }
        """
        cache_key = "ollama"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached["timestamp"] < self._cache_ttl:
                return cached["data"]

        result = {"status": "unknown", "latency_ms": 0, "models": [], "error": None}

        try:
            start = datetime.utcnow()
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=2.0)
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000

                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "unknown") for m in data.get("models", [])]
                    result = {
                        "status": "healthy",
                        "latency_ms": int(elapsed),
                        "models": models,
                        "error": None,
                    }
                    logger.info(
                        f"Ollama healthy: {len(models)} models, {elapsed:.0f}ms"
                    )
                else:
                    result = {
                        "status": "error",
                        "latency_ms": int(elapsed),
                        "models": [],
                        "error": f"HTTP {response.status_code}",
                    }
                    logger.warning(f"Ollama error: HTTP {response.status_code}")

        except httpx.ConnectError:
            result = {
                "status": "offline",
                "latency_ms": 0,
                "models": [],
                "error": "Connection refused",
            }
            logger.error("Ollama OFFLINE: Connection refused")

        except asyncio.TimeoutError:
            result = {
                "status": "offline",
                "latency_ms": 2000,
                "models": [],
                "error": "Timeout after 2s",
            }
            logger.error("Ollama OFFLINE: Timeout")

        except Exception as e:
            result = {"status": "error", "latency_ms": 0, "models": [], "error": str(e)}
            logger.error(f"Ollama error: {e}")

        # Update cache
        self._cache[cache_key] = {"timestamp": datetime.utcnow(), "data": result}

        return result

    async def check_nvidia(self, use_cache: bool = True) -> Dict:
        """
        Check if NVIDIA API is accessible and key is valid.

        Returns:
            {
                "status": "configured" | "missing_key" | "error",
                "key_valid": bool,
                "error": str (if error)
            }
        """
        cache_key = "nvidia"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached["timestamp"] < self._cache_ttl:
                return cached["data"]

        result = {"status": "unknown", "key_valid": False, "error": None}

        # Check API key
        if not settings.NVIDIA_API_KEY:
            result = {
                "status": "missing_key",
                "key_valid": False,
                "error": "NVIDIA_API_KEY not set",
            }
            logger.warning("NVIDIA API: Missing API key")
            return result

        if not settings.NVIDIA_API_KEY.startswith("nvapi-"):
            result = {
                "status": "invalid_key",
                "key_valid": False,
                "error": "Invalid key format (should start with nvapi-)",
            }
            logger.warning("NVIDIA API: Invalid key format")
            return result

        # Try to list models (validates key)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.nvidia_url}/models",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    result = {"status": "configured", "key_valid": True, "error": None}
                    logger.info("NVIDIA API: Key valid, service accessible")
                else:
                    result = {
                        "status": "error",
                        "key_valid": False,
                        "error": f"HTTP {response.status_code}",
                    }
                    logger.warning(f"NVIDIA API error: HTTP {response.status_code}")

        except Exception as e:
            result = {"status": "error", "key_valid": False, "error": str(e)}
            logger.error(f"NVIDIA API error: {e}")

        # Update cache
        self._cache[cache_key] = {"timestamp": datetime.utcnow(), "data": result}

        return result

    async def check_all(self, use_cache: bool = True) -> Dict:
        """
        Check all backends and return summary.

        Returns:
            {
                "ollama": {...},
                "nvidia": {...},
                "any_available": bool,
                "recommended_action": str
            }
        """
        ollama_health = await self.check_ollama(use_cache)
        nvidia_health = await self.check_nvidia(use_cache)

        ollama_ok = ollama_health["status"] == "healthy"
        nvidia_ok = nvidia_health["status"] == "configured"

        any_available = ollama_ok or nvidia_ok

        # Recommended action
        if not any_available:
            recommended = "PAUSE_QUEUE: No backends available"
        elif not ollama_ok and nvidia_ok:
            recommended = "ROUTE_TO_NVIDIA: Ollama unavailable"
        elif ollama_ok and not nvidia_ok:
            recommended = "ROUTE_TO_OLLAMA: NVIDIA API unavailable"
        else:
            recommended = "NORMAL: All backends healthy"

        return {
            "ollama": ollama_health,
            "nvidia": nvidia_health,
            "any_available": any_available,
            "recommended_action": recommended,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def should_process_tasks(self) -> tuple[bool, str]:
        """
        Quick check if worker should process tasks.

        Returns:
            (should_process: bool, reason: str)
        """
        health = await self.check_all(use_cache=True)

        if not health["any_available"]:
            return False, "No backends available - pausing task processing"

        if (
            health["ollama"]["status"] != "healthy"
            and health["nvidia"]["status"] != "configured"
        ):
            return False, "All backends unhealthy"

        return True, health["recommended_action"]

    def clear_cache(self):
        """Clear health check cache"""
        self._cache.clear()
        logger.info("Health check cache cleared")


# Singleton
_backend_checker: BackendHealthChecker = None


def get_backend_checker() -> BackendHealthChecker:
    """Get or create backend health checker singleton"""
    global _backend_checker
    if _backend_checker is None:
        _backend_checker = BackendHealthChecker()
    return _backend_checker
