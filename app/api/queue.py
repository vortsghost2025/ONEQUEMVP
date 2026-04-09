from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Dict
import httpx
import os

from app.models import Settings, Task
from app.utils import get_session, logger

router = APIRouter()


# GET /queue/status – returns the pause flag and simple counts
@router.get("/status", response_model=Dict[str, int | bool])
def get_queue_status(session: Session = Depends(get_session)):
    logger.debug("Getting queue status")
    # Retrieve the singleton Settings row (create if missing – should already exist)
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
        session.commit()
        session.refresh(settings)

    pending = len(session.exec(select(Task).where(Task.status == "pending")).all())
    running = len(session.exec(select(Task).where(Task.status == "running")).all())
    logger.debug(
        f"Queue status: paused={settings.queue_paused}, pending={pending}, running={running}"
    )
    return {
        "queue_paused": settings.queue_paused,
        "pending_count": pending,
        "running_count": running,
    }


# POST /queue/pause – set manual pause flag
@router.post("/pause", status_code=status.HTTP_200_OK)
def pause_queue(session: Session = Depends(get_session)):
    logger.info("Pausing queue")
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
    settings.queue_paused = True
    session.add(settings)
    session.commit()
    session.refresh(settings)
    logger.info("Queue paused")
    return {"queue_paused": settings.queue_paused}


# POST /queue/resume – clear manual pause flag
@router.post("/resume", status_code=status.HTTP_200_OK)
def resume_queue(session: Session = Depends(get_session)):
    logger.info("Resuming queue")
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
    settings.queue_paused = False
    session.add(settings)
    session.commit()
    session.refresh(settings)
    logger.info("Queue resumed")
    return {"queue_paused": settings.queue_paused}


# POST /queue/clear-failed – delete all tasks that have failed
@router.post("/clear-failed", status_code=status.HTTP_200_OK)
def clear_failed_tasks(session: Session = Depends(get_session)):
    logger.info("Clearing failed tasks")
    failed_tasks = session.exec(select(Task).where(Task.status == "failed")).all()
    if not failed_tasks:
        logger.debug("No failed tasks to clear")
        return {"deleted": 0}
    for t in failed_tasks:
        session.delete(t)
    session.commit()
    logger.info(f"Cleared {len(failed_tasks)} failed tasks")
    return {"deleted": len(failed_tasks)}


@router.get("/health")
async def system_health():
    """Check health of all connected services."""
    from app.config import settings

    health = {
        "backend": "healthy",
        "ollama": "unknown",
        "nvidia_api": "unknown",
        "nvidia_key_loaded": bool(settings.NVIDIA_API_KEY),
    }

    # Check Ollama
    ollama_url = settings.OLLAMA_BASE_URL
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                health["ollama"] = "healthy"
            else:
                health["ollama"] = f"error_{response.status_code}"
    except Exception as e:
        health["ollama"] = f"offline"

    # Check NVIDIA API key
    if settings.NVIDIA_API_KEY and settings.NVIDIA_API_KEY.startswith("nvapi-"):
        health["nvidia_api"] = "configured"
    elif settings.NVIDIA_API_KEY:
        health["nvidia_api"] = "invalid_format"
    else:
        health["nvidia_api"] = "missing_key"

    return health
