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