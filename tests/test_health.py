"""
Test health endpoint and API health checks
"""
import pytest


class TestHealthEndpoint:
    def test_health_endpoint(self, client):
        """Test the /health endpoint returns proper response"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "onequeue-api"


class TestMainHealth:
    def test_health_returns_expected_structure(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data

    def test_health_status_value(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]