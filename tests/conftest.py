import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["NVIDIA_API_KEY"] = ""


@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(engine):
    with patch("app.services.monitor.psutil.disk_usage") as mock_disk:
        mock_disk.return_value = MagicMock(percent=50)
        
        from app.main import app, get_session
        
        def override_get_session():
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session

        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def task_data():
    return {
        "title": "Test Task",
        "prompt": "Write a test message",
        "model": "llama3",
        "priority": 5,
        "timeout_seconds": 60,
        "max_retries": 2,
    }
