import httpx
from typing import Dict, Any, Optional
from app.config import settings


class KiloGateway:
    def __init__(self):
        self.api_key = settings.KILO_API_KEY
        self.base_url = settings.KILO_GATEWAY_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat_completion(
        self,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("KILO_API_KEY not configured")

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

    async def chat_completion_stream(
        self,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        if not self.is_configured():
            raise ValueError("KILO_API_KEY not configured")

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
                            import json

                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get(
                                "delta", {}
                            ).get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue


kilo_gateway = KiloGateway()