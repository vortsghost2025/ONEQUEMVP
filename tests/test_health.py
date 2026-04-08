"""
Test health endpoint
"""
import pytest


class TestHealthEndpoint:
    def test_health_endpoint_not_found(self, client):
        response = client.get("/health")
        assert response.status_code == 404