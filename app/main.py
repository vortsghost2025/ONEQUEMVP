"""FastAPI entry‑point for the OneQueue service.

All heavy lifting (engine, logger, DB session) now lives in ``app.utils`` to
avoid circular imports with the API routers.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, select, Session, text

# Shared utilities (engine, logger, get_session)
from app.utils import engine, logger, get_session

# Routers – they depend on ``get_session`` from utils
from app.api import (
    tasks,
    settings as settings_router,
    queue as queue_router,
    nvidia as nvidia_router,
    router_api,
    ai_idea,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    # Pre-flight checklist
    from app.services.preflight import run_preflight_checklist

    logger.info("Running pre-flight checklist...")
    if not await run_preflight_checklist():
        logger.error("Pre-flight failed")
        import sys

        sys.exit(1)

    logger.info("Pre-flight passed")

    # Database setup
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

    # Default settings
    with Session(engine) as session:
        from app.models import Settings

        if not session.get(Settings, 1):
            session.add(Settings())
            session.commit()

    # Recover crashed tasks
    with Session(engine) as session:
        from app.models import Task, TaskStatus

        running_tasks = session.exec(
            select(Task).where(Task.status == TaskStatus.RUNNING)
        ).all()
        for task in running_tasks:
            task.status = TaskStatus.FAILED
            session.add(task)
        if running_tasks:
            session.commit()
            logger.info(f"Recovered {len(running_tasks)} tasks")

    # Start worker
    from app import worker as _worker

    worker_task = asyncio.create_task(_worker.worker_loop())
    logger.info("Worker started")

    # Start service monitor
    from app.services.service_monitor import start_service_monitoring

    await start_service_monitoring(interval_seconds=60)
    logger.info("Service monitor started")

    # Integrate graceful shutdown
    from app.services.graceful_shutdown import integrate_with_fastapi

    integrate_with_fastapi(app)

    yield

    # Shutdown
    from app.services.service_monitor import stop_service_monitoring

    stop_service_monitoring()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Worker stopped")


# FastAPI application instance
app = FastAPI(title="OneQueue API", version="0.2.1", lifespan=lifespan)

# CORS configuration – same origins as before
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://[::1]:5173",
        "http://[::1]:5174",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://[::1]:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers – batch endpoint defined before parameterized routes
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
app.include_router(queue_router.router, prefix="/queue", tags=["queue"])
app.include_router(nvidia_router.router, prefix="/nvidia", tags=["nvidia"])
app.include_router(router_api.router, prefix="/router", tags=["router"])
app.include_router(ai_idea.router, prefix="/ai-idea", tags=["ai-idea"])
app.include_router(router_api.router, tags=["openai"])


# Exception handlers – preserve existing behaviour
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health_check():
    """Health check endpoint for orchestration platforms."""
    return {"status": "healthy", "service": "onequeue-api"}
