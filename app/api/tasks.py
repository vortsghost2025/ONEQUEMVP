from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.models import Task, TaskStatus, Run
from app.utils import get_session, logger

router = APIRouter()


# Pydantic models for request/response bodies
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    prompt: str = Field(..., min_length=1, max_length=100000)
    model: Optional[str] = Field(default="llama3", max_length=100)
    priority: Optional[int] = Field(default=5, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(default=120, ge=10, le=3600)
    max_retries: Optional[int] = Field(default=2, ge=0, le=5)

    @validator("title")
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @validator("prompt")
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()


class TaskPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    prompt: Optional[str] = Field(default=None, min_length=1, max_length=100000)
    model: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(default=None, ge=10, le=3600)
    max_retries: Optional[int] = Field(default=None, ge=0, le=5)

    @validator("title", "prompt", always=True)
    def validate_optional_fields(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip() if v else v


# Batch task creation for high-throughput scenarios
class TaskBatchCreate(BaseModel):
    tasks: List[TaskCreate] = Field(..., min_length=1, max_length=100)

    @validator("tasks")
    def validate_tasks(cls, v):
        if not v:
            raise ValueError("At least one task required")
        return v


# =============================================================================
# ROUTES MUST BE ORDERED: Specific routes BEFORE parameterized routes!
# =============================================================================

# Batch create tasks - MUST come before /{task_id}
@router.post("/batch", response_model=List[Task], status_code=status.HTTP_201_CREATED)
def create_task_batch(batch: TaskBatchCreate, session: Session = Depends(get_session)):
    """Create multiple tasks in a single transaction for better throughput."""
    logger.info(f"Creating batch of {len(batch.tasks)} tasks")
    
    tasks = [
        Task(
            title=task.title,
            prompt=task.prompt,
            model=task.model or "llama3",
            priority=task.priority or 5,
            timeout_seconds=task.timeout_seconds or 120,
            max_retries=task.max_retries or 2,
        )
        for task in batch.tasks
    ]
    
    session.add_all(tasks)
    session.commit()
    
    # Refresh all to get IDs
    for task in tasks:
        session.refresh(task)
    
    logger.info(f"Created batch of {len(tasks)} tasks")
    return tasks


# List tasks - MUST come before /{task_id}
@router.get("", response_model=List[Task])
def list_tasks(
    status: Optional[TaskStatus] = None, session: Session = Depends(get_session)
):
    logger.debug(f"Listing tasks with status filter: {status}")
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    tasks = session.exec(stmt).all()
    logger.debug(f"Found {len(tasks)} tasks")
    return tasks


# Create a new task
@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, session: Session = Depends(get_session)):
    logger.info(f"Creating task: {task_in.title[:50]}...")
    task = Task(
        title=task_in.title,
        prompt=task_in.prompt,
        model=task_in.model or "llama3",
        priority=task_in.priority or 5,
        timeout_seconds=task_in.timeout_seconds or 120,
        max_retries=task_in.max_retries or 2,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"Created task id={task.id}")
    return task


# Get a task by ID - Parameterized route comes LAST
@router.get("/{task_id}", response_model=Task)
def read_task(task_id: int, session: Session = Depends(get_session)):
    logger.debug(f"Reading task id={task_id}")
    task = session.get(Task, task_id)
    if not task:
        logger.warning(f"Task not found: id={task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Patch (partial update) a task
@router.patch("/{task_id}", response_model=Task)
def patch_task(
    task_id: int, task_update: TaskPatch, session: Session = Depends(get_session)
):
    logger.info(f"Patching task id={task_id}")
    task = session.get(Task, task_id)
    if not task:
        logger.warning(f"Task not found for patch: id={task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"Patched task id={task_id}")
    return task


# Cancel a task
@router.post("/{task_id}/cancel", response_model=Task)
def cancel_task(task_id: int, session: Session = Depends(get_session)):
    logger.info(f"Cancel requested for task id={task_id}")
    task = session.get(Task, task_id)
    if not task:
        logger.warning(f"Task not found for cancel: id={task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    task.cancel_requested = True
    if task.status == TaskStatus.RUNNING:
        task.status = TaskStatus.CANCELLED
        task.finished_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"Cancelled task id={task_id}, status={task.status}")
    return task


# Retry a task
@router.post("/{task_id}/retry", response_model=Task)
def retry_task(task_id: int, session: Session = Depends(get_session)):
    logger.info(f"Retry requested for task id={task_id}")
    task = session.get(Task, task_id)
    if not task:
        logger.warning(f"Task not found for retry: id={task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        logger.warning(f"Invalid retry attempt for task id={task_id}, status={task.status}")
        raise HTTPException(
            status_code=400, detail="Only failed or cancelled tasks can be retried"
        )
    task.attempt_count += 1
    task.status = TaskStatus.PENDING
    task.cancel_requested = False
    task.output_text = None
    task.error_text = None
    task.started_at = None
    task.finished_at = None

    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"Retried task id={task_id}, new attempt_count={task.attempt_count}")
    return task
