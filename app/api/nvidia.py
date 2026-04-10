from fastapi import APIRouter, HTTPException
from app.services.nvidia_api import NvidiaAPI
import logging
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("onequeue")
router = APIRouter()
nvidia_api = NvidiaAPI()


class GenerateRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=200, description="Model name")
    prompt: str = Field(..., min_length=1, max_length=100000, description="Prompt text")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Max tokens to generate")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    system_prompt: Optional[str] = Field(default=None, max_length=10000, description="System prompt")


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
async def generate_text(request: GenerateRequest):
    logger.info(f"NVIDIA generate request for model: {request.model}")
    try:
        result = await nvidia_api.generate(
            model=request.model,
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt,
        )

        logger.info(f"NVIDIA generate successful for model: {request.model}")
        return {
            "model": request.model,
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
