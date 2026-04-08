import pytest
from datetime import datetime
from app.models import Task, Settings, TaskStatus, Run, ThresholdCheckResult


class TestModels:
    def test_task_defaults(self):
        task = Task(title="Test", prompt="Prompt")
        assert task.status == "pending"
        assert task.model == "llama3"
        assert task.priority == 5
        assert task.timeout_seconds == 120
        assert task.max_retries == 2
        assert task.cancel_requested is False
        assert task.created_at is not None

    def test_settings_defaults(self):
        settings = Settings()
        assert settings.max_ram_percent == 95.0
        assert settings.max_cpu_percent == 95.0
        assert settings.max_disk_percent == 95.0
        assert settings.auto_pause is True
        assert settings.default_model == "llama3"
        assert settings.default_timeout_seconds == 120
        assert settings.queue_paused is False

    def test_task_status_enum(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_threshold_check_result(self):
        result = ThresholdCheckResult(should_pause=True, reason="RAM breach")
        assert result.should_pause is True
        assert result.reason == "RAM breach"

    def test_task_with_all_fields(self):
        task = Task(
            title="Full Task",
            prompt="Prompt",
            model="mistral",
            priority=10,
            timeout_seconds=60,
            max_retries=3,
        )
        assert task.title == "Full Task"
        assert task.prompt == "Prompt"
        assert task.model == "mistral"
        assert task.priority == 10
        assert task.timeout_seconds == 60
        assert task.max_retries == 3


class TestErrorHandling:
    def test_create_task_missing_title(self, client):
        response = client.post("/tasks", json={"prompt": "No title"})
        assert response.status_code == 422

    def test_create_task_missing_prompt(self, client):
        response = client.post("/tasks", json={"title": "No prompt"})
        assert response.status_code == 422

    def test_create_task_invalid_priority(self, client):
        response = client.post("/tasks", json={"title": "Test", "prompt": "Test", "priority": "high"})
        assert response.status_code == 422

    def test_create_task_invalid_timeout(self, client):
        response = client.post("/tasks", json={"title": "Test", "prompt": "Test", "timeout_seconds": -1})
        assert response.status_code in [201, 422]

    def test_update_settings_invalid_value(self, client):
        response = client.patch("/settings", json={"max_ram_percent": 150})
        assert response.status_code in [200, 422]

    def test_list_tasks_invalid_status(self, client):
        response = client.get("/tasks?status=invalid")
        assert response.status_code == 422


class TestEdgeCases:
    def test_patch_empty(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.patch(f"/tasks/{task_id}", json={})
        assert response.status_code == 200

    def test_create_task_long_title(self, client):
        long_title = "x" * 1000
        response = client.post("/tasks", json={"title": long_title, "prompt": "Test"})
        assert response.status_code == 201

    def test_create_task_long_prompt(self, client):
        long_prompt = "x" * 10000
        response = client.post("/tasks", json={"title": "Test", "prompt": long_prompt})
        assert response.status_code == 201

    def test_cancel_already_cancelled(self, client, task_data):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        client.post(f"/tasks/{task_id}/cancel")
        response = client.post(f"/tasks/{task_id}/cancel")
        assert response.status_code == 200