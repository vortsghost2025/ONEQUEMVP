"""
AI Idea Planner API Endpoint
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.ai_idea_planner import get_planner

router = APIRouter()


class IdeaRequest(BaseModel):
    message: str


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
    try:
        planner = get_planner()
        result = await planner.parse_idea(request.message)
        return IdeaResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
