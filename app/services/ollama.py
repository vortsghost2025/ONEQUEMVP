import httpx
from app.config import settings


class OllamaError(RuntimeError):
    """Custom exception for Ollama‑related failures."""

    pass


class OllamaClient:
    """Thin async wrapper around the Ollama HTTP API.

    The client uses the ``OLLAMA_BASE_URL`` from the bootstrap config.
    Supports routing to local GPU (via Tailscale) when PREFER_LOCAL_GPU is True.
    It provides two convenience methods used by the queue worker:
    * ``check_health`` – verifies that the Ollama server is reachable.
    * ``generate`` – sends a prompt to a model and returns the generated text.
    """

    def __init__(self) -> None:
        # Ensure we always have a trailing slash‑less URL for consistent concatenation
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.gpu_url = (
            settings.OLLAMA_GPU_URL.rstrip("/") if settings.OLLAMA_GPU_URL else None
        )
        self.prefer_gpu = settings.PREFER_LOCAL_GPU

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        """Add :latest suffix to model name if missing."""
        if model and ":" not in model:
            return f"{model}:latest"
        return model

    async def check_health(self) -> bool:
        """Ping the Ollama ``/api/tags`` endpoint.

        Returns ``True`` if the request succeeds with a 200 status code within
        a 2‑second timeout, otherwise ``False``.
        """
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False

    async def check_gpu_health(self) -> bool:
        """Check if GPU backend (via Tailscale) is available."""
        if not self.gpu_url:
            return False
        url = f"{self.gpu_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False

    def get_backend_url(self, prefer_gpu: bool = True) -> str:
        """Return the appropriate backend URL based on preference."""
        if prefer_gpu and self.gpu_url:
            return self.gpu_url
        return self.base_url

    async def generate(self, prompt: str, model: str, timeout: int) -> str:
        """Generate text from Ollama.

        Parameters
        ----------
        prompt: str
            The prompt to send to the model.
        model: str
            The model name (e.g. ``"llama3"``).
        timeout: int
            HTTP timeout in seconds – the Ollama server itself respects this
            value when performing the generation.

        Returns
        -------
        str
            The generated response text.

        Raises
        ------
        OllamaError
            If the API returns a non‑200 status or includes an ``error`` field.
        """
        normalized_model = self._normalize_model_name(model)
        backend_url = self.get_backend_url(self.prefer_gpu)
        url = f"{backend_url}/api/generate"
        payload = {"model": normalized_model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise OllamaError(data["error"])
                # Ollama returns the generated text under the ``response`` key
                return data.get("response", "")
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise OllamaError(str(exc)) from exc


# ─────────────────────────────────────────────
# Module-level convenience wrappers
# ─────────────────────────────────────────────
# These allow OpenAIProxy and router_api to call
# `ollama.generate()` without instantiating OllamaClient.

_client = OllamaClient()


def _normalize_model_name(model: str) -> str:
    """Add :latest suffix to model name if missing."""
    if model and ":" not in model:
        return f"{model}:latest"
    return model


async def generate(prompt: str, model: str, timeout: int = 120) -> str:
    """
    Module-level wrapper for OllamaClient.generate().

    Used by OpenAIProxy to route requests to local Ollama models.

    Parameters:
    -----------
    prompt: str
        The prompt to send to the model
    model: str
        The model name (e.g., "llama3", "mistral")
    timeout: int
        HTTP timeout in seconds (default: 120)

    Returns:
    --------
    str
        The generated response text
    """
    normalized_model = _normalize_model_name(model)
    return await _client.generate(prompt, normalized_model, timeout)


async def check_health() -> bool:
    """
    Module-level wrapper for OllamaClient.check_health().

    Used by service monitor and health checks.

    Returns:
    --------
    bool
        True if Ollama is reachable, False otherwise
    """
    return await _client.check_health()


async def check_gpu_health() -> bool:
    """
    Module-level wrapper for OllamaClient.check_gpu_health().

    Returns:
    --------
    bool
        True if GPU backend is reachable, False otherwise
    """
    return await _client.check_gpu_health()
