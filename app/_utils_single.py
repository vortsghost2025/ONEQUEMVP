"""Utility module shared across the OneQueue code‑base.

This file hosts objects that are imported by several other modules:

* ``engine`` – the SQLModel engine configured with a connection pool.
* ``logger`` – the central ``onequeue`` logger.
* ``get_session`` – a FastAPI dependency that yields a ``Session``.

Moving these definitions out of ``app.main`` eliminates the circular import
between ``app.main`` and ``app.api.tasks``.  All modules that require a DB
session or logging should import from ``app.utils``.
"""

import logging
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine, select, text
from app.config import settings
from app.models import Task, Settings, TaskStatus

# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("onequeue")

# ---------------------------------------------------------------------------
# Database engine with connection pooling for high‑concurrency workloads
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,            # Base number of persistent connections
    max_overflow=30,         # Additional connections under load
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=3600,       # Recycle connections after 1 hour
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a SQLModel ``Session``.

    The session is scoped to a single request and closed automatically when
    the generator exits.
    """
    with Session(engine) as session:
        yield session
