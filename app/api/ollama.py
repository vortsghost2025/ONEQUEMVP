from fastapi import APIRouter, HTTPException
import logging
import httpx
from app import utils

logger = logging.getLogger("onequeue")
router = APIRouter()

DEFAULT_OLLAMA_MODELS = [
    "llama3:latest",
    "llama3.1:latest",
    "mistral:latest",
    "codellama:7b",
    "qwen2.5-coder:7b",
    "llama3:8b",
    "mistral:7b",
]


@router.get("/models")
async def list_ollama_models():
    """List available Ollama models from local instance"""
    from app import utils
    settings = utils.get_settings()
    
    models = []
    ollama_urls = [settings.OLLAMA_BASE_URL]
    if settings.OLLAMA_GPU_URL:
        ollama_urls.append(settings.OLLAMA_GPU_URL)
    
    for url in ollama_urls:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/api/tags", timeout=3.0)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    logger.info(f"Ollama at {url}: {len(models)} models")
                    return {"models": models, "count": len(models)}
        except Exception as e:
            logger.debug(f"Ollama not available at {url}: {e}")
            continue
    
    return {"models": DEFAULT_OLLAMA_MODELS, "count": len(DEFAULT_OLLAMA_MODELS), "source": "defaults"}
