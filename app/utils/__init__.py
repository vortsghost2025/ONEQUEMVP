"""Shared utilities for the OneQueue application."""

import logging
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite specific
    pool_size=10,  # Base connections
    max_overflow=20,  # Additional connections under load
    pool_pre_ping=True,  # Verify connections
    pool_recycle=1800,  # Recycle after 30 min
)


def get_session():
    """Get database session."""
    return Session(engine)


__all__ = ["engine", "logger", "get_session"]
