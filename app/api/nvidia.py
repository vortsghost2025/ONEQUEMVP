from fastapi import APIRouter, HTTPException
from app.services.nvidia_api import NvidiaAPI
import logging

logger = logging.getLogger("onequeue")
router = APIRouter()
nvidia_api = NvidiaAPI()


@router.get("/models")
async def list_nvidia_models():
    try:
        models = await nvidia_api.list_models()
        return {"models": models, "count": len(models)}
    except Exception as e:
        logger.error(f"Failed to list NVIDIA models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/curated")
async def get_curated_models():
    try:
        models = nvidia_api.get_curated_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to get curated models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_text(request: dict):
    try:
        model = request.get("model")
        prompt = request.get("prompt")
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        system_prompt = request.get("system_prompt")

        if not model or not prompt:
            raise HTTPException(status_code=400, detail="model and prompt are required")

        result = await nvidia_api.generate(
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )

        return {
            "model": model,
            "response": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NVIDIA generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate")
async def validate_api_key():
    try:
        is_valid = nvidia_api.validate_key()
        return {"valid": is_valid}
    except Exception as e:
        logger.error(f"API key validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
