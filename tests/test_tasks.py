import pytest
from app.models import Task, TaskStatus
from sqlmodel import select, update


class TestTasksAPI:
    def test_create_task(self, client, task_data):
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["prompt"] == task_data["prompt"]
        assert data["model"] == task_data["model"]
        assert data["status"] == "pending"
        assert data["priority"] == task_data["priority"]
        assert "id" in data

    def test_create_task_defaults(self, client):
        response = client.post("/tasks", json={"title": "Simple", "prompt": "Hello"})
        assert response.status_code == 201
        data = response.json()
        assert data["model"] == "llama3"
        assert data["priority"] == 5
        assert data["timeout_seconds"] == 120
        assert data["max_retries"] == 2

    def test_get_task(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == task_data["title"]

    def test_get_task_not_found(self, client):
        response = client.get("/tasks/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_list_tasks(self, client, task_data):
        client.post("/tasks", json=task_data)
        client.post("/tasks", json={**task_data, "title": "Second Task"})

        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_tasks_filter_by_status(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.get("/tasks?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "pending" for t in data)

    def test_patch_task(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.patch(f"/tasks/{task_id}", json={"title": "Updated Title", "priority": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["priority"] == 10

    def test_patch_task_not_found(self, client):
        response = client.patch("/tasks/99999", json={"title": "New"})
        assert response.status_code == 404

    def test_cancel_task(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.post(f"/tasks/{task_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["cancel_requested"] is True

    def test_cancel_task_not_found(self, client):
        response = client.post("/tasks/99999/cancel")
        assert response.status_code == 404

    def test_retry_task(self, client, task_data, session):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        session.exec(update(Task).where(Task.id == task_id).values(status="failed"))
        session.commit()

        response = client.post(f"/tasks/{task_id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["attempt_count"] == 2

    def test_retry_task_wrong_status(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.post(f"/tasks/{task_id}/retry")
        assert response.status_code == 400
        assert "failed or cancelled" in response.json()["detail"]

    def test_retry_task_not_found(self, client):
        response = client.post("/tasks/99999/retry")
        assert response.status_code == 404
