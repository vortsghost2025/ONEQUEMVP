# Consolidated model package for OneQueue
# This file now exports both the core SQLModel ORM definitions and the Pydantic
# chat schemas used across the API. The previous top‑level ``models.py`` conflicted
# with the ``app/models`` package, causing ``ImportError: cannot import name 'Task'``
# during runtime. By moving the definitions into the package's ``__init__`` we keep
# the original import style (``from app.models import Task``) intact.

# ------------------------------------------------------------
# Core SQLModel entities (previously in app/models.py)
# ------------------------------------------------------------
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid, time


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Settings(SQLModel, table=True):
    """Singleton row (id=1) storing mutable runtime settings."""

    id: int = Field(default=1, primary_key=True)
    max_ram_percent: float = Field(default=95.0)
    max_cpu_percent: float = Field(default=95.0)
    max_disk_percent: float = Field(default=95.0)
    auto_pause: bool = Field(default=True)
    default_model: str = Field(default="llama3")
    default_timeout_seconds: int = Field(default=120)
    queue_paused: bool = Field(default=False)
    breach_duration_seconds: int = Field(default=5)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    prompt: str
    model: str = Field(default="llama3")
    status: str = Field(default="pending")  # matches TaskStatus values
    priority: int = Field(default=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    timeout_seconds: int = Field(default=120)
    attempt_count: int = Field(default=1)
    max_retries: int = Field(default=2)
    output_text: Optional[str] = None
    error_text: Optional[str] = None
    cancel_requested: bool = Field(default=False)
    runs: List["Run"] = Relationship(back_populates="task")


class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    attempt_number: int
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    duration_ms: int
    success: bool
    token_estimate: Optional[int] = None
    error_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    task: Task = Relationship(back_populates="runs")


# ------------------------------------------------------------
# Additional Pydantic contracts used by the OpenAI proxy
# ------------------------------------------------------------
from pydantic import BaseModel, Field
from typing import Any, List, Literal, Optional, Union


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str
    name: Optional[str] = None

    class Config:
        extra = "allow"


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, gt=0)
    stream: Optional[bool] = Field(default=False)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[Union[str, List[str]]] = None
    user: Optional[str] = None

    class Config:
        extra = "allow"


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


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "onequeue"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]


# ------------------------------------------------------------
# Service monitoring result type
# ------------------------------------------------------------
class ThresholdCheckResult(BaseModel):
    should_pause: bool
    reason: Optional[str] = None
