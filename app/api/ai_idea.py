"""
AI Idea Planner API Endpoint
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

from app.ai_idea_planner import get_planner

logger = logging.getLogger("onequeue")
router = APIRouter()


class IdeaRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=50000, description="User's idea message")


class IdeaResponse(BaseModel):
    response: str
    taskPlan: Dict[str, Any] | None = None


@router.post("/", response_model=IdeaResponse)
async def parse_idea(request: IdeaRequest):
    """
    Parse a user's idea and return a structured task plan.

    This endpoint:
    1. Takes natural language input
    2. Uses LLM to break it into structured tasks
    3. Returns task plan for approval
    """
    logger.info(f"AI Idea request received, message length: {len(request.message)}")
    try:
        planner = get_planner()
        result = await planner.parse_idea(request.message)
        logger.info("AI Idea request completed successfully")
        return IdeaResponse(**result)
    except Exception as e:
        logger.error(f"AI Idea request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
