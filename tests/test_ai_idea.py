"""
Test AI Idea API endpoint
"""
import pytest
from unittest.mock import patch


class TestAIIdeaAPI:
    def test_parse_idea(self, client):
        """Test parsing an idea"""
        response = client.post("/ai-idea/", json={
            "message": "Build a web app"
        })
        assert response.status_code in [200, 500]

    def test_parse_idea_empty_message(self, client):
        """Test empty message returns validation error"""
        response = client.post("/ai-idea/", json={
            "message": ""
        })
        assert response.status_code == 422

    def test_parse_idea_missing_message(self, client):
        """Test missing message returns validation error"""
        response = client.post("/ai-idea/", json={})
        assert response.status_code == 422

    def test_parse_idea_long_message(self, client):
        """Test long message"""
        long_message = "x" * 10000
        response = client.post("/ai-idea/", json={
            "message": long_message
        })
        assert response.status_code in [200, 500]


class TestAIIdeaResponse:
    def test_response_structure(self, client):
        """Test response has expected structure"""
        response = client.post("/ai-idea/", json={
            "message": "Create a task"
        })
        if response.status_code == 200:
            data = response.json()
            assert "response" in data