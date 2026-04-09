"""
OpenAI-Compatible Proxy for OneQueue
Makes OneQueue work like OpenAI API for universal compatibility
"""

import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("onequeue.proxy")


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


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageStats


class OpenAIProxy:
    """OpenAI-compatible API wrapper for OneQueue"""

    def __init__(self):
        self._nvidia_api = None
        self._ollama_api = None
        self._smart_router = None

    @property
    def nvidia_api(self):
        if self._nvidia_api is None:
            from app.services.nvidia_api import NvidiaAPI

            self._nvidia_api = NvidiaAPI()
        return self._nvidia_api

    @property
    def ollama_api(self):
        if self._ollama_api is None:
            from app.services import ollama

            self._ollama_api = ollama
        return self._ollama_api

    @property
    def smart_router(self):
        if self._smart_router is None:
            from app.services.smart_router import SmartRouter

            self._smart_router = SmartRouter()
        return self._smart_router

    def _generate_id(self) -> str:
        return f"chatcmpl-{uuid.uuid4().hex[:12]}"

    def _get_timestamp(self) -> int:
        return int(time.time())

    def _is_nvidia_model(self, model_id: str) -> bool:
        return "/" in model_id and not model_id.startswith("ollama")

    async def create_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Create non-streaming chat completion"""
        model_id = request.model

            # Smart routing for "auto" model
            if model_id == "auto":
                prompt_text = "\n".join([f"{m.role}: {m.content}" for m in request.messages])
                model_id, model_info = self.smart_router.select_model(prompt_text)
                logger.info(f"Smart routing (streaming): auto -> {model_id}")

            prompt = "\n".join([f"{m.role}: {m.content}" for m in request.messages])

            try:
                if self._is_nvidia_model(model_id):
                    from app.services.nvidia_api import NvidiaAPI

                    nvidia_api = NvidiaAPI()
                    async for chunk in nvidia_api.generate_stream(
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
                        yield f"data: {json.dumps(data)}\n\n"

                    final = {
                        "id": self._generate_id(),
                        "object": "chat.completion.chunk",
                        "created": self._get_timestamp(),
                        "model": model_id,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(final)}\n\n"
                    yield "data: [DONE]\n\n"

                else:
                    from app.services import ollama

                    content = await ollama.generate(
                        prompt=prompt, model=model_id, timeout=120
                    )

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
                    yield f"data: {json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"

            except Exception as e:
                error_msg = {"error": {"message": str(e), "type": "streaming_error"}}
                yield f"data: {json.dumps(error_msg)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    def list_models(self) -> Dict[str, Any]:
        """List all available models (OpenAI-compatible)"""
        models = []

        for model_id, info in self.smart_router.models.items():
            models.append(
                {
                    "id": model_id,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": model_id.split("/")[0] if "/" in model_id else "local",
                }
            )

        return {"object": "list", "data": models}

    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get model information"""
        info = self.smart_router.get_model_info(model_id)

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
