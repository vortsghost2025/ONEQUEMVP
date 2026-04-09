"""
Pure data contracts - no imports from anywhere in this project.
This file can be imported by ANYONE without risk of circular dependency.
"""

import time
import uuid
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional, Union


# ─────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str
    name: Optional[str] = None

    class Config:
        extra = "allow"


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature between 0 and 2"
    )
    max_tokens: Optional[int] = Field(
        default=2048, gt=0, description="Maximum tokens to generate"
    )
    stream: Optional[bool] = Field(
        default=False, description="Whether to stream responses via SSE"
    )
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[Union[str, List[str]]] = None
    user: Optional[str] = None

    class Config:
        extra = "allow"


# ─────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"
    logprobs: Optional[Any] = None


class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageStats
    system_fingerprint: Optional[str] = None


# ─────────────────────────────────────────────
# Model List Response (for /v1/models)
# ─────────────────────────────────────────────


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "onequeue"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]
