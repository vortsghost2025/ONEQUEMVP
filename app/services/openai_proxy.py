"""
OpenAI-Compatible Proxy for OneQueue
Makes OneQueue work like OpenAI API for universal compatibility
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger("onequeue.proxy")


# OpenAI-compatible request models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[List[str]] = None
    user: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class OpenAIProxy:
    """OpenAI-compatible API wrapper for OneQueue"""

    def __init__(self, nvidia_api, ollama_api, smart_router):
        self.nvidia_api = nvidia_api
        self.ollama_api = ollama_api
        self.router = smart_router

    def _is_nvidia_model(self, model_id: str) -> bool:
        """Check if model is from NVIDIA"""
        nvidia_prefixes = [
            "meta/",
            "deepseek-ai/",
            "nvidia/",
            "qwen/",
            "google/",
            "microsoft/",
            "mistralai/",
        ]
        return any(model_id.startswith(prefix) for prefix in nvidia_prefixes)

    def _generate_id(self) -> str:
        """Generate unique completion ID"""
        return f"chatcmpl-{uuid.uuid4().hex[:12]}"

    def _get_timestamp(self) -> int:
        """Get current Unix timestamp"""
        return int(time.time())

    async def create_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Create a chat completion (OpenAI-compatible)"""

        # Extract the last user message
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message provided")

        prompt = user_messages[-1].content

        # Determine model
        model_id = request.model

        # If auto, use smart routing
        if model_id == "auto" or model_id == "smart":
            model_id, _ = self.router.select_model(
                prompt=prompt,
                prefer_quality=request.temperature < 0.5,
                prefer_speed=request.temperature > 0.9,
            )

        # Route to appropriate API
        try:
            if self._is_nvidia_model(model_id):
                response = await self.nvidia_api.generate(
                    model=model_id,
                    prompt=prompt,
                    max_tokens=request.max_tokens or 2048,
                    temperature=request.temperature or 0.7,
                )
                content = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                usage = response.get(
                    "usage",
                    {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                )
            else:
                # Ollama
                content = await self.ollama_api.generate(
                    prompt=prompt, model=model_id, timeout=120
                )
                usage = {
                    "prompt_tokens": len(prompt) // 4,
                    "completion_tokens": len(content) // 4,
                    "total_tokens": (len(prompt) + len(content)) // 4,
                }

            # Format response to match OpenAI API
            completion = ChatCompletionResponse(
                id=self._generate_id(),
                created=self._get_timestamp(),
                model=model_id,
                choices=[
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                usage=usage,
            )

            return completion

        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def stream_chat_completion(self, request: ChatCompletionRequest):
        """Stream chat completion (SSE format)"""

        # Extract prompt
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message provided")

        prompt = user_messages[-1].content
        model_id = request.model

        if model_id == "auto" or model_id == "smart":
            model_id, _ = self.router.select_model(prompt=prompt)

        async def generate_stream():
            try:
                if self._is_nvidia_model(model_id):
                    # Stream from NVIDIA
                    async for chunk in self.nvidia_api.generate_stream(
                        model=model_id,
                        prompt=prompt,
                        max_tokens=request.max_tokens or 2048,
                        temperature=request.temperature or 0.7,
                    ):
                        data = {
                            "id": self._generate_id(),
                            "object": "chat.completion.chunk",
                            "created": self._get_timestamp(),
                            "model": model_id,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": chunk},
                                    "finish_reason": None,
                                }
                            ],
                        }
                        yield f"data: {self._json.dumps(data)}\n\n"

                    # Send final chunk
                    final = {
                        "id": self._generate_id(),
                        "object": "chat.completion.chunk",
                        "created": self._get_timestamp(),
                        "model": model_id,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {self._json.dumps(final)}\n\n"
                    yield "data: [DONE]\n\n"

                else:
                    # Ollama doesn't support streaming in this version
                    content = await self.ollama_api.generate(
                        prompt=prompt, model=model_id, timeout=120
                    )

                    # Send as single chunk
                    data = {
                        "id": self._generate_id(),
                        "object": "chat.completion.chunk",
                        "created": self._get_timestamp(),
                        "model": model_id,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                    yield f"data: {self._json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"

            except Exception as e:
                error_msg = {"error": str(e)}
                yield f"data: {self._json.dumps(error_msg)}\n\n"

        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    def list_models(self) -> Dict[str, Any]:
        """List all available models (OpenAI-compatible)"""
        models = []

        # Add NVIDIA models
        for model_id, info in self.router.models.items():
            if info.provider == "nvidia":
                models.append(
                    {
                        "id": model_id,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": model_id.split("/")[0],
                    }
                )

        # Add Ollama models
        for model_id, info in self.router.models.items():
            if info.provider == "ollama":
                models.append(
                    {
                        "id": model_id,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "local",
                    }
                )

        return {"object": "list", "data": models}

    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get model information"""
        info = self.router.get_model_info(model_id)

        if not info:
            raise HTTPException(status_code=404, detail="Model not found")

        return {
            "id": model_id,
            "object": "model",
            "created": 1700000000,
            "owned_by": model_id.split("/")[0] if "/" in model_id else "local",
            "permission": [],
            "root": model_id,
            "parent": None,
            "context_length": info.context_length,
            "tier": info.tier,
        }


# FastAPI router for OpenAI-compatible endpoints
def create_openai_router(proxy: OpenAIProxy) -> APIRouter:
    """Create FastAPI router with OpenAI-compatible endpoints"""
    router = APIRouter()

    @router.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        """OpenAI-compatible chat completion endpoint"""
        if request.stream:
            return await proxy.stream_chat_completion(request)
        else:
            return await proxy.create_chat_completion(request)

    @router.get("/v1/models")
    async def list_models():
        """List all available models"""
        return proxy.list_models()

    @router.get("/v1/models/{model_id}")
    async def get_model(model_id: str):
        """Get model information"""
        return proxy.get_model(model_id)

    @router.post("/v1/completions")
    async def completions(request: Dict):
        """Legacy completions endpoint (for compatibility)"""
        # Convert to chat format
        chat_request = ChatCompletionRequest(
            model=request.get("model", "llama3:latest"),
            messages=[{"role": "user", "content": request.get("prompt", "")}],
            max_tokens=request.get("max_tokens", 100),
            temperature=request.get("temperature", 0.7),
            stream=request.get("stream", False),
        )

        if chat_request.stream:
            return await proxy.stream_chat_completion(chat_request)
        else:
            return await proxy.create_chat_completion(chat_request)

    return router
