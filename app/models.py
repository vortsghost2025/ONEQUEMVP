from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


# ---------- Task status enum ----------
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------- Settings singleton (persisted) ----------
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


# ---------- Task model ----------
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


# ---------- Run model ----------
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


# ---------- Threshold check result (service) ----------
class ThresholdCheckResult(BaseModel):
    should_pause: bool
    reason: Optional[str] = None
