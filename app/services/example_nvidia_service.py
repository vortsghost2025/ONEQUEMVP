"""
Example: Using NVIDIA API Key Rotation in Your Services

This file demonstrates how to integrate automatic API key rotation
into your existing NVIDIA API service classes.
"""

import requests
from typing import Dict, Any
from app.services.nvidia_rotation import nvidia_api_retry_with_rotation
from app.services.nvidia_key_rotation import get_rotator, get_current_key


class NvidiaServiceWithRotation:
    """
    Example NVIDIA service with automatic key rotation.

    Features:
    - Automatic 429 detection
    - Key rotation on rate limit
    - Exponential backoff
    - Key health tracking
    """

    def __init__(self, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self.base_url = base_url

    @nvidia_api_retry_with_rotation
    def chat_completion(self, model: str, messages: list) -> Dict[str, Any]:
        """
        Generate chat completion with automatic key rotation.

        Args:
            model: Model name (e.g., "meta/llama-3.1-405b-instruct")
            messages: List of message dicts

        Returns:
            Completion response dict
        """
        key = get_current_key()

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            timeout=30,
        )

        # Raise exception on error (will trigger rotation logic)
        response.raise_for_status()

        return response.json()

    @nvidia_api_retry_with_rotation
    def generate(self, prompt: str, model: str = "meta/llama-3.1-70b-instruct") -> str:
        """
        Simple generation with automatic key rotation.

        Args:
            prompt: Text prompt
            model: Model name

        Returns:
            Generated text
        """
        key = get_current_key()

        response = requests.post(
            f"{self.base_url}/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "prompt": prompt, "max_tokens": 256},
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        return data.get("choices", [{}])[0].get("text", "")

    def get_key_status(self) -> Dict:
        """Get status of all API keys."""
        rotator = get_rotator()
        return rotator.get_status()


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = NvidiaServiceWithRotation()

    # Example 1: Simple generation
    try:
        result = service.generate("Hello, how are you?")
        print(f"Generated: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Chat completion
    try:
        result = service.chat_completion(
            model="meta/llama-3.1-405b-instruct",
            messages=[
                {
                    "role": "user",
                    "content": "Explain quantum computing in one sentence.",
                }
            ],
        )
        print(f"Chat response: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 3: Check key status
    status = service.get_key_status()
    print(f"Key status: {status}")
