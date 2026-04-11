import pytest


class TestSettingsAPI:
    def test_get_settings(self, client):
        response = client.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert "max_ram_percent" in data
        assert "max_cpu_percent" in data
        assert "default_model" in data

    def test_update_settings(self, client):
        response = client.patch("/settings", json={
            "max_ram_percent": 80.0,
            "default_model": "mistral",
            "auto_pause": False
        })
        assert response.status_code == 200
        data = response.json()
        assert data["max_ram_percent"] == 80.0
        assert data["default_model"] == "mistral"
        assert data["auto_pause"] is False

    def test_update_settings_partial(self, client):
        response = client.patch("/settings", json={"max_cpu_percent": 75.0})
        assert response.status_code == 200
        data = response.json()
        assert data["max_cpu_percent"] == 75.0

    def test_settings_persists(self, client):
        client.patch("/settings", json={"default_timeout_seconds": 300})
        response = client.get("/settings")
        assert response.json()["default_timeout_seconds"] == 300


class TestSettingsValidation:
    def test_update_settings_invalid_ram(self, client):
        response = client.patch("/settings", json={"max_ram_percent": 150})
        assert response.status_code == 422

    def test_update_settings_negative_ram(self, client):
        response = client.patch("/settings", json={"max_ram_percent": -10})
        assert response.status_code == 422

    def test_update_settings_invalid_cpu(self, client):
        response = client.patch("/settings", json={"max_cpu_percent": 150})
        assert response.status_code == 422

    def test_update_settings_invalid_timeout(self, client):
        response = client.patch("/settings", json={"default_timeout_seconds": 5})
        assert response.status_code == 422

    def test_update_settings_timeout_too_large(self, client):
        response = client.patch("/settings", json={"default_timeout_seconds": 5000})
        assert response.status_code == 422

    def test_update_settings_empty_model(self, client):
        response = client.patch("/settings", json={"default_model": "   "})
        assert response.status_code == 422


class TestSettingsDefaults:
    def test_default_values(self, client):
        response = client.get("/settings")
        data = response.json()
        assert data["max_ram_percent"] == 95.0
        assert data["max_cpu_percent"] == 95.0
        assert data["max_disk_percent"] == 95.0
        assert data["auto_pause"] is True
        assert data["default_model"] == "llama3"
        assert data["default_timeout_seconds"] == 120
        assert data["queue_paused"] is False

    def test_breach_duration_default(self, client):
        response = client.get("/settings")
        data = response.json()
        assert "breach_duration_seconds" in data
        assert data["breach_duration_seconds"] == 5


class TestSettingsMultiple:
    def test_update_multiple_settings(self, client):
        response = client.patch("/settings", json={
            "max_ram_percent": 85.0,
            "max_cpu_percent": 90.0,
            "auto_pause": False,
            "default_model": "codellama"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["max_ram_percent"] == 85.0
        assert data["max_cpu_percent"] == 90.0
        assert data["auto_pause"] is False
        assert data["default_model"] == "codellama"

    def test_all_settings_persist(self, client):
        client.patch("/settings", json={
            "max_ram_percent": 80.0,
            "max_cpu_percent": 85.0,
            "max_disk_percent": 90.0,
            "default_model": "mixtral",
            "default_timeout_seconds": 180,
            "queue_paused": True
        })
        response = client.get("/settings")
        data = response.json()
        assert data["max_ram_percent"] == 80.0
        assert data["max_cpu_percent"] == 85.0
        assert data["max_disk_percent"] == 90.0
        assert data["default_model"] == "mixtral"
        assert data["default_timeout_seconds"] == 180
        assert data["queue_paused"] is True