import pytest
from app.models import Task
from sqlmodel import select, update


class TestQueueAPI:
    def test_get_queue_status_empty(self, client):
        response = client.get("/queue/status")
        assert response.status_code == 200
        data = response.json()
        assert "queue_paused" in data
        assert "pending_count" in data
        assert "running_count" in data

    def test_get_queue_status_with_tasks(self, client, task_data):
        client.post("/tasks", json=task_data)
        client.post("/tasks", json={**task_data, "title": "Task 2"})

        response = client.get("/queue/status")
        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] >= 2

    def test_pause_queue(self, client):
        response = client.post("/queue/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["queue_paused"] is True

        status_response = client.get("/queue/status")
        assert status_response.json()["queue_paused"] is True

    def test_resume_queue(self, client):
        client.post("/queue/pause")
        response = client.post("/queue/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["queue_paused"] is False

    def test_clear_failed_tasks_none(self, client):
        response = client.post("/queue/clear-failed")
        assert response.status_code == 200
        assert response.json()["deleted"] == 0

    def test_clear_failed_tasks_with_failed(self, client, task_data, session):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        session.exec(update(Task).where(Task.id == task_id).values(status="failed"))
        session.commit()

        response = client.post("/queue/clear-failed")
        assert response.status_code == 200
        assert response.json()["deleted"] == 1

        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404