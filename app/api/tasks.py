from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.models import Task, TaskStatus, Run
from app.main import get_session

router = APIRouter()


# Pydantic models for request/response bodies
class TaskCreate(BaseModel):
    title: str
    prompt: str
    model: Optional[str] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None


# Create a new task
@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, session: Session = Depends(get_session)):
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
    return task


# Get a task by ID
@router.get("/{task_id}", response_model=Task)
def read_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Patch (partial update) a task
@router.patch("/{task_id}", response_model=Task)
def patch_task(
    task_id: int, task_update: TaskPatch, session: Session = Depends(get_session)
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# Cancel a task
@router.post("/{task_id}/cancel", response_model=Task)
def cancel_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.cancel_requested = True
    if task.status == TaskStatus.RUNNING:
        task.status = TaskStatus.CANCELLED
        task.finished_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# Retry a task
@router.post("/{task_id}/retry", response_model=Task)
def retry_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
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
    return task


# List tasks (optional filtering)
@router.get("", response_model=List[Task])
def list_tasks(
    status: Optional[TaskStatus] = None, session: Session = Depends(get_session)
):
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    tasks = session.exec(stmt).all()
    return tasks
