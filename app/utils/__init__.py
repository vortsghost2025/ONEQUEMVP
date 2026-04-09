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

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite specific
)


def get_session():
    """Get database session."""
    return Session(engine)


__all__ = ["engine", "logger", "get_session"]
