import os
import httpx
from typing import Dict, Any, List, Optional
import json
from app.config import settings


class NvidiaAPI:
    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> List[Dict[str, str]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/models", headers=self.headers, timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return [
                {"id": m["id"], "owned_by": m.get("owned_by", "unknown")}
                for m in data["data"]
            ]

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get(
                                "delta", {}
                            ).get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue

    def validate_key(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("nvapi-"))

    def get_curated_models(self) -> List[Dict[str, str]]:
        return [
            {
                "id": "meta/llama-4-maverick-17b-128e-instruct",
                "name": "Llama 4 Maverick",
                "tier": "flagship",
                "category": "general",
            },
            {
                "id": "meta/llama-4-scout-17b-16e-instruct",
                "name": "Llama 4 Scout",
                "tier": "flagship",
                "category": "general",
            },
            {
                "id": "deepseek-ai/deepseek-v3.2",
                "name": "DeepSeek V3.2",
                "tier": "flagship",
                "category": "reasoning",
            },
            {
                "id": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "name": "Nemotron Super 49B",
                "tier": "flagship",
                "category": "general",
            },
            {
                "id": "meta/llama-3.1-405b-instruct",
                "name": "Llama 3.1 405B",
                "tier": "flagship",
                "category": "general",
            },
            {
                "id": "mistralai/mistral-large-3-675b-instruct-2512",
                "name": "Mistral Large 3",
                "tier": "flagship",
                "category": "general",
            },
            {
                "id": "google/gemma-4-31b-it",
                "name": "Gemma 4 31B",
                "tier": "fast",
                "category": "general",
            },
            {
                "id": "microsoft/phi-4-mini-instruct",
                "name": "Phi 4 Mini",
                "tier": "fast",
                "category": "general",
            },
            {
                "id": "qwen/qwen3-coder-480b-a35b-instruct",
                "name": "Qwen Coder 480B",
                "tier": "coding",
                "category": "coding",
            },
            {
                "id": "deepseek-ai/deepseek-r1-distill-llama-8b",
                "name": "DeepSeek R1 Distill",
                "tier": "reasoning",
                "category": "reasoning",
            },
        ]
