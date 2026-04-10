from fastapi import APIRouter, HTTPException
from app.services import ollama
import logging
import httpx

logger = logging.getLogger("onequeue")
router = APIRouter()


@router.get("/models")
async def list_ollama_models():
    try:
        client = ollama._client
        url = f"{client.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=5.0) as httpx_client:
            resp = await httpx_client.get(url)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name", "unknown") for m in data.get("models", [])]
            return {"models": models, "count": len(models)}
    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        return {"models": [], "count": 0, "error": str(e)}


@router.get("/health")
async def check_ollama_health():
    try:
        is_healthy = await ollama.check_health()
        return {"status": "healthy" if is_healthy else "unhealthy", "service": "ollama"}
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return {"status": "error", "service": "ollama", "error": str(e)}