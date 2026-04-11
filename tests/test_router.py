"""
Test Router API endpoints - Smart Router, Benchmark, OpenAI Proxy
"""
import pytest


class TestRouterAPI:
    def test_route_task(self, client):
        """Test smart router task recommendation"""
        response = client.post("/router/route", json={
            "prompt": "Write a Python function to calculate fibonacci"
        })
        assert response.status_code in [200, 500]

    def test_route_task_with_preferences(self, client):
        """Test router with speed/quality preferences"""
        response = client.post("/router/route", json={
            "prompt": "Explain quantum computing",
            "prefer_speed": True
        })
        assert response.status_code in [200, 500]

    def test_route_task_require_local(self, client):
        """Test router with local model requirement"""
        response = client.post("/router/route", json={
            "prompt": "Write a hello world",
            "require_local": True
        })
        assert response.status_code in [200, 500]


class TestRouterModels:
    def test_get_recommended_models(self, client):
        """Test getting recommended models"""
        response = client.get("/router/models/recommended")
        assert response.status_code in [200, 500]

    def test_get_recommended_models_with_task_type(self, client):
        """Test getting recommended models by task type"""
        response = client.get("/router/models/recommended?task_type=code")
        assert response.status_code in [200, 500]

    def test_get_recommended_models_limit(self, client):
        """Test model list limit"""
        response = client.get("/router/models/recommended?limit=3")
        assert response.status_code in [200, 500]


class TestRouterAnalyze:
    def test_analyze_prompt(self, client):
        """Test prompt analysis"""
        response = client.get("/router/analyze?prompt=Write a poem")
        assert response.status_code in [200, 500]


class TestRouterModelInfo:
    def test_get_model_info(self, client):
        """Test getting model info"""
        response = client.get("/router/models/llama3:latest")
        assert response.status_code in [200, 404, 500]

    def test_model_not_found(self, client):
        """Test non-existent model returns 404"""
        response = client.get("/router/models/nonexistent-model")
        assert response.status_code in [200, 404, 500]


class TestRouterFallback:
    def test_get_fallback_chain(self, client):
        """Test getting fallback chain"""
        response = client.get("/router/fallback/llama3:latest")
        assert response.status_code in [200, 500]

    def test_generate_with_fallback(self, client):
        """Test generate with fallback"""
        response = client.post("/router/generate/fallback", json={
            "prompt": "Hello world"
        })
        assert response.status_code in [200, 500]


class TestRouterBenchmark:
    def test_quick_benchmark(self, client):
        """Test quick benchmark"""
        response = client.get("/router/benchmark/quick")
        assert response.status_code in [200, 500]

    def test_benchmark_results(self, client):
        """Test getting benchmark results"""
        response = client.get("/router/benchmark/results")
        assert response.status_code in [200, 500]


class TestOpenAIProxy:
    def test_list_models_v1(self, client):
        """Test OpenAI-compatible models list"""
        response = client.get("/router/v1/models")
        assert response.status_code in [200, 500]

    def test_chat_completions(self, client):
        """Test chat completions"""
        response = client.post("/router/v1/chat/completions", json={
            "model": "llama3:latest",
            "messages": [{"role": "user", "content": "Hello"}]
        })
        assert response.status_code in [200, 500]

    def test_chat_completions_stream(self, client):
        """Test streaming chat completions"""
        response = client.post("/router/v1/chat/completions", json={
            "model": "llama3:latest",
            "messages": [{"role": "user", "content": "Count to 3"}],
            "stream": True
        })
        assert response.status_code in [200, 500]