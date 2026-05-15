import httpx
import threading
import time
import logging
from typing import Dict, Any, List, Optional
import json
from app.config import settings

logger = logging.getLogger("onequeue.nvidia")


class KeyPool:
    def __init__(self, keys: List[str]):
        self._keys = [k for k in keys if k.startswith("nvapi-")]
        self._index = 0
        self._lock = threading.Lock()
        self._errors: Dict[str, int] = {}
        self._cool_until: Dict[str, float] = {}

    @property
    def available(self) -> bool:
        return len(self._keys) > 0

    @property
    def count(self) -> int:
        return len(self._keys)

    def get(self) -> Optional[str]:
        with self._lock:
            now = time.monotonic()
            for _ in range(len(self._keys)):
                idx = self._index % len(self._keys)
                key = self._keys[idx]
                self._index = idx + 1
                cool = self._cool_until.get(key, 0)
                if now >= cool:
                    return key
            return self._keys[0] if self._keys else None

    def report_error(self, key: str, cooldown: float = 30.0):
        with self._lock:
            self._errors[key] = self._errors.get(key, 0) + 1
            self._cool_until[key] = time.monotonic() + cooldown
            logger.warning(
                f"Key ...{key[-6:]} error #{self._errors[key]}, cooling {cooldown}s"
            )

    def report_success(self, key: str):
        with self._lock:
            self._errors.pop(key, None)
            self._cool_until.pop(key, None)

    def status(self) -> List[Dict[str, Any]]:
        now = time.monotonic()
        result = []
        for key in self._keys:
            result.append(
                {
                    "key_suffix": key[-6:],
                    "errors": self._errors.get(key, 0),
                    "cooling": now < self._cool_until.get(key, 0),
                    "cooldown_remaining": max(0, self._cool_until.get(key, 0) - now),
                }
            )
        return result


pool = KeyPool(settings.get_nvidia_keys())


class NvidiaAPI:
    def __init__(self):
        self.base_url = "https://integrate.api.nvidia.com/v1"

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> List[Dict[str, str]]:
        key = pool.get()
        if not key:
            raise RuntimeError("No NVIDIA API keys available")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers=self._headers(key),
                timeout=30.0,
            )
            if response.status_code in (401, 429):
                pool.report_error(
                    key, cooldown=60.0 if response.status_code == 429 else 10.0
                )
                raise RuntimeError(f"NVIDIA API error {response.status_code}")
            response.raise_for_status()
            pool.report_success(key)
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

        key = pool.get()
        if not key:
            raise RuntimeError("No NVIDIA API keys available")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(key),
                json=payload,
                timeout=120.0,
            )
            if response.status_code in (401, 429):
                pool.report_error(
                    key, cooldown=60.0 if response.status_code == 429 else 10.0
                )
                raise RuntimeError(f"NVIDIA API error {response.status_code}")
            response.raise_for_status()
            pool.report_success(key)
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

        key = pool.get()
        if not key:
            raise RuntimeError("No NVIDIA API keys available")
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(key),
                json=payload,
                timeout=120.0,
            ) as response:
                if response.status_code in (401, 429):
                    pool.report_error(
                        key, cooldown=60.0 if response.status_code == 429 else 10.0
                    )
                    raise RuntimeError(f"NVIDIA API error {response.status_code}")
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
                pool.report_success(key)

    def validate_key(self) -> bool:
        return pool.available

    def get_key_pool_status(self) -> List[Dict[str, Any]]:
        return pool.status()

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
