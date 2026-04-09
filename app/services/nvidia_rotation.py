"""
Convenience decorators for NVIDIA API key rotation.

Usage:
    from app.services.nvidia_rotation import nvidia_api_retry_with_rotation

    class NvidiaService:
        @nvidia_api_retry_with_rotation
        def generate_completion(self, prompt: str):
            response = requests.post(API_URL, headers={"Authorization": f"Bearer {get_current_key()}"})
            response.raise_for_status()
            return response.json()
"""

from functools import wraps
from typing import Callable, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import logging

from .nvidia_key_rotation import (
    get_rotator,
    record_success,
    record_failure,
    rotate_key,
    NVIDIAKeyRotator,
)

logger = logging.getLogger(__name__)


def nvidia_api_retry_with_rotation(func: Callable) -> Callable:
    """
    Decorator for NVIDIA API calls with automatic key rotation on 429.

    Features:
    - Retries with exponential backoff
    - Rotates to next API key on rate limit (429)
    - Tracks key health and failures
    - Maximum 3 retries per key before rotating

    Usage:
        @nvidia_api_retry_with_rotation
        def call_nvidia_api(prompt: str):
            key = get_current_key()
            response = requests.post(...)
            response.raise_for_status()
            return response.json()
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        rotator = get_rotator()
        last_exception = None

        # Try with current key, then rotate and retry
        for attempt in range(3):  # Max 3 attempts with different keys
            try:
                result = func(*args, **kwargs)
                record_success()
                return result

            except Exception as e:
                last_exception = e
                status_code = None

                # Extract status code if available
                if hasattr(e, "response") and e.response is not None:
                    status_code = e.response.status_code
                elif hasattr(e, "args") and len(e.args) > 0:
                    if isinstance(e.args[0], int):
                        status_code = e.args[0]

                # Record failure (auto-rotates on 429)
                record_failure(status_code)

                # If it's a 429, try rotating
                if status_code == 429:
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/3), rotating keys..."
                    )
                    if not rotate_key():
                        logger.error("Cannot rotate - no more keys available")
                        raise
                else:
                    # For other errors, re-raise immediately
                    raise

        # If we get here, all attempts failed
        logger.error(f"All attempts failed: {last_exception}")
        raise last_exception

    return wrapper


def with_key_rotation(func: Callable) -> Callable:
    """
    Simpler decorator that just handles key rotation without retry logic.
    Use this when you have your own retry logic but want key rotation.

    Usage:
        @with_key_rotation
        def my_api_call():
            key = get_current_key()
            # ... make call
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            record_success()
            return result
        except Exception as e:
            status_code = None

            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
            elif hasattr(e, "args") and len(e.args) > 0:
                if isinstance(e.args[0], int):
                    status_code = e.args[0]

            record_failure(status_code)
            raise

    return wrapper
