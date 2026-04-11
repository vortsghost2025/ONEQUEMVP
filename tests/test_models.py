import pytest
from datetime import datetime
from sqlmodel import update
from app.models import (
    Task, Settings, TaskStatus, Run, ThresholdCheckResult,
    ChatMessage, ChatCompletionRequest, ChatCompletionResponse,
    ModelCard, ModelListResponse
)


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


class TestSettingsModel:
    def test_settings_singleton_id(self):
        settings = Settings()
        assert settings.id == 1

    def test_settings_custom_values(self):
        settings = Settings(
            max_ram_percent=80.0,
            max_cpu_percent=85.0,
            auto_pause=False,
            default_model="mixtral",
            default_timeout_seconds=180
        )
        assert settings.max_ram_percent == 80.0
        assert settings.max_cpu_percent == 85.0
        assert settings.auto_pause is False
        assert settings.default_model == "mixtral"
        assert settings.default_timeout_seconds == 180

    def test_settings_queue_control(self):
        settings = Settings(queue_paused=True)
        assert settings.queue_paused is True

    def test_settings_breach_duration(self):
        settings = Settings(breach_duration_seconds=10)
        assert settings.breach_duration_seconds == 10


class TestRunModel:
    def test_run_creation(self):
        run = Run(
            task_id=1,
            attempt_number=1,
            cpu_percent=50.0,
            ram_percent=60.0,
            disk_percent=40.0,
            duration_ms=1500,
            success=True,
            token_estimate=100
        )
        assert run.task_id == 1
        assert run.attempt_number == 1
        assert run.cpu_percent == 50.0
        assert run.ram_percent == 60.0
        assert run.disk_percent == 40.0
        assert run.duration_ms == 1500
        assert run.success is True
        assert run.token_estimate == 100
        assert run.created_at is not None


class TestChatSchemas:
    def test_chat_message_user(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_message_system(self):
        msg = ChatMessage(role="system", content="You are helpful")
        assert msg.role == "system"

    def test_chat_message_assistant(self):
        msg = ChatMessage(role="assistant", content="Response", name="assistant")
        assert msg.role == "assistant"
        assert msg.name == "assistant"

    def test_chat_completion_request_defaults(self):
        req = ChatCompletionRequest(
            model="llama3",
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert req.model == "llama3"
        assert req.temperature == 0.7
        assert req.max_tokens == 2048
        assert req.stream is False

    def test_chat_completion_request_with_params(self):
        req = ChatCompletionRequest(
            model="mistral",
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.9,
            max_tokens=1000,
            top_p=0.8
        )
        assert req.temperature == 0.9
        assert req.max_tokens == 1000
        assert req.top_p == 0.8

    def test_model_card(self):
        card = ModelCard(id="llama3:latest")
        assert card.id == "llama3:latest"
        assert card.object == "model"
        assert card.owned_by == "onequeue"

    def test_model_list_response(self):
        cards = [ModelCard(id="llama3"), ModelCard(id="mistral")]
        response = ModelListResponse(data=cards)
        assert len(response.data) == 2
        assert response.object == "list"


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

    def test_retry_cancelled_task(self, client, task_data, session):
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        session.exec(update(Task).where(Task.id == task_id).values(status="cancelled"))
        session.commit()
        
        response = client.post(f"/tasks/{task_id}/retry")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"