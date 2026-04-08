import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings


# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("onequeue")

# Create the database engine
engine = create_engine(settings.DATABASE_URL, echo=False)


# Dependency for DB sessions
from typing import Generator
from sqlmodel import select
from app.models import Task, Settings, TaskStatus


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# Import routers after get_session is defined to avoid circular imports
from app.api import tasks, settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Create all tables
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created (if not existing)")

    # Ensure singleton Settings exists
    with Session(engine) as session:
        settings_row = session.get(Settings, 1)
        if not settings_row:
            session.add(Settings())
            session.commit()
        logger.info("Created default Settings singleton")

    # Startup recovery: mark any RUNNING tasks as FAILED
    with Session(engine) as session:
        running_tasks = session.exec(
            select(Task).where(Task.status == TaskStatus.RUNNING)
        ).all()
        for task in running_tasks:
            task.status = TaskStatus.FAILED
            task.error_text = "Worker interrupted by restart"
            task.finished_at = datetime.utcnow()
            session.add(task)
        if running_tasks:
            session.commit()
            logger.info(f"Recovered {len(running_tasks)} RUNNING tasks as FAILED")

    # Start the background worker
    from app import worker as _worker

    worker_task = asyncio.create_task(_worker.worker_loop())
    logger.info("Background worker started")

    yield  # Application runs here

    # Shutdown: cancel the worker task
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Background worker stopped")


# FastAPI instance
app = FastAPI(title="OneQueue API", version="0.1.0", lifespan=lifespan)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (they will import get_session from this module)
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
from app.api import queue as queue_router

app.include_router(queue_router.router, prefix="/queue", tags=["queue"])


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Tables and Settings are created in lifespan context manager above
