from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Dict

from app.models import Settings, Task
from app.main import get_session

router = APIRouter()


# GET /queue/status – returns the pause flag and simple counts
@router.get("/status", response_model=Dict[str, int | bool])
def get_queue_status(session: Session = Depends(get_session)):
    # Retrieve the singleton Settings row (create if missing – should already exist)
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
        session.commit()
        session.refresh(settings)

    pending = len(session.exec(select(Task).where(Task.status == "pending")).all())
    running = len(session.exec(select(Task).where(Task.status == "running")).all())
    return {
        "queue_paused": settings.queue_paused,
        "pending_count": pending,
        "running_count": running,
    }


# POST /queue/pause – set manual pause flag
@router.post("/pause", status_code=status.HTTP_200_OK)
def pause_queue(session: Session = Depends(get_session)):
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
    settings.queue_paused = True
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return {"queue_paused": settings.queue_paused}


# POST /queue/resume – clear manual pause flag
@router.post("/resume", status_code=status.HTTP_200_OK)
def resume_queue(session: Session = Depends(get_session)):
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
    settings.queue_paused = False
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return {"queue_paused": settings.queue_paused}


# POST /queue/clear-failed – delete all tasks that have failed
@router.post("/clear-failed", status_code=status.HTTP_200_OK)
def clear_failed_tasks(session: Session = Depends(get_session)):
    failed_tasks = session.exec(select(Task).where(Task.status == "failed")).all()
    if not failed_tasks:
        return {"deleted": 0}
    for t in failed_tasks:
        session.delete(t)
    session.commit()
    return {"deleted": len(failed_tasks)}
