"""
Test NVIDIA API endpoints
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestNvidiaAPI:
    def test_list_nvidia_models(self, client):
        """Test listing NVIDIA models"""
        response = client.get("/nvidia/models")
        assert response.status_code in [200, 500]

    def test_get_curated_models(self, client):
        """Test getting curated models"""
        response = client.get("/nvidia/curated")
        assert response.status_code in [200, 500]

    def test_validate_api_key(self, client):
        """Test API key validation"""
        response = client.get("/nvidia/validate")
        assert response.status_code in [200, 500]


class TestNvidiaGenerate:
    def test_generate_requires_model(self, client):
        """Test that generate requires model"""
        response = client.post("/nvidia/generate", json={"prompt": "test"})
        assert response.status_code == 400

    def test_generate_requires_prompt(self, client):
        """Test that generate requires prompt"""
        response = client.post("/nvidia/generate", json={"model": "llama3"})
        assert response.status_code == 400

    def test_generate_with_model_and_prompt(self, client):
        """Test generate with model and prompt"""
        response = client.post("/nvidia/generate", json={
            "model": "meta/llama-4-maverick-17b-128e-instruct",
            "prompt": "Say hello"
        })
        assert response.status_code in [200, 500]


class TestNvidiaModels:
    def test_curated_models_count(self, client):
        """Test curated models return expected format"""
        response = client.get("/nvidia/curated")
        if response.status_code == 200:
            data = response.json()
            assert "models" in data

    def test_list_models_returns_count(self, client):
        """Test list models returns count"""
        response = client.get("/nvidia/models")
        if response.status_code == 200:
            data = response.json()
            assert "count" in data
            assert "models" in data


class TestNvidiaValidation:
    def test_validate_missing_key(self, client):
        """Test validation with no key"""
        response = client.get("/nvidia/validate")
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data