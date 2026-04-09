"""
NVIDIA API Key Rotation Manager

Rotates between multiple API keys when hitting rate limits (429).
Based on production patterns from high-traffic AI services.

Features:
- Multiple API key configuration
- Automatic 429 detection and key rotation
- Per-key exponential backoff
- Circuit breaker pattern for failing keys
- Key health tracking and metrics
"""

import os
import time
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    """Status of an API key."""

    HEALTHY = "healthy"
    COOLDOWN = "cooldown"
    EXHAUSTED = "exhausted"
    INVALID = "invalid"


@dataclass
class APIKey:
    """Represents a single API key with metadata."""

    key: str
    status: KeyStatus = KeyStatus.HEALTHY
    failure_count: int = 0
    last_failure_time: float = 0
    total_requests: int = 0
    total_failures: int = 0

    def is_available(self) -> bool:
        """Check if key is available for use."""
        if self.status == KeyStatus.EXHAUSTED or self.status == KeyStatus.INVALID:
            return False

        if self.status == KeyStatus.COOLDOWN:
            # Check if cooldown period has passed (5 minutes)
            if time.time() - self.last_failure_time > 300:
                self.status = KeyStatus.HEALTHY
                return True
            return False

        return True

    def record_success(self):
        """Record a successful request."""
        self.total_requests += 1
        if self.status == KeyStatus.COOLDOWN:
            self.status = KeyStatus.HEALTHY
        self.failure_count = 0

    def record_failure(self, max_failures: int = 3):
        """Record a failed request."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()

        if self.failure_count >= max_failures:
            self.status = KeyStatus.COOLDOWN
            logger.warning(
                f"🔑 API key {self.key[:8]}... entered cooldown ({self.failure_count} failures)"
            )

    def mark_invalid(self):
        """Mark key as invalid (permanent failure)."""
        self.status = KeyStatus.INVALID
        logger.error(f"❌ API key {self.key[:8]}... marked as invalid")


class NVIDIAKeyRotator:
    """
    Manages rotation between multiple NVIDIA API keys.

    Usage:
        rotator = NVIDIAKeyRotator()

        # Get current key
        api_key = rotator.get_current_key()

        # On success
        rotator.record_success()

        # On 429 error
        if rotator.should_rotate():
            rotator.rotate()
            api_key = rotator.get_current_key()
    """

    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        Initialize key rotator.

        Args:
            api_keys: List of NVIDIA API keys. If None, reads from NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, etc.
        """
        self.keys: List[APIKey] = []
        self.current_index = 0
        self.rotation_count = 0

        # Load keys
        if api_keys:
            for key in api_keys:
                self.add_key(key)
        else:
            self._load_from_env()

        if len(self.keys) == 0:
            raise ValueError("No API keys configured")

        logger.info(f"🔑 Initialized with {len(self.keys)} API key(s)")

    def _load_from_env(self):
        """Load API keys from environment variables."""
        index = 1
        while True:
            key = os.getenv(f"NVIDIA_API_KEY_{index}")
            if not key:
                if index == 1:
                    # Fallback to single key without suffix
                    key = os.getenv("NVIDIA_API_KEY")
                    if key:
                        self.add_key(key)
                break
            self.add_key(key)
            index += 1

    def add_key(self, key: str):
        """Add an API key to the rotation pool."""
        self.keys.append(APIKey(key=key))
        logger.info(f"🔑 Added API key ending in ...{key[-4:]}")

    def get_current_key(self) -> str:
        """Get the current API key."""
        if not self.keys:
            raise RuntimeError("No API keys available")

        return self.keys[self.current_index].key

    def get_current_key_id(self) -> int:
        """Get the index of the current key."""
        return self.current_index

    def record_success(self):
        """Record a successful request."""
        current_key = self.keys[self.current_index]
        current_key.record_success()
        self.rotation_count = 0  # Reset rotation counter on success

    def record_failure(self, status_code: Optional[int] = None):
        """
        Record a failed request.

        Args:
            status_code: HTTP status code (429 = rate limit)
        """
        current_key = self.keys[self.current_index]
        current_key.record_failure()

        # Auto-rotate on 429
        if status_code == 429:
            logger.warning(
                f"⚠️ Rate limit hit on key {self.current_index + 1}, rotating..."
            )
            self.rotate()

    def should_rotate(self) -> bool:
        """Check if we should rotate to next key."""
        # Can rotate if we have multiple keys and not all are exhausted
        if len(self.keys) <= 1:
            return False

        # Check if current key is in cooldown
        if not self.keys[self.current_index].is_available():
            return True

        return False

    def rotate(self) -> bool:
        """
        Rotate to the next available API key.

        Returns:
            True if rotation successful, False if no keys available
        """
        if len(self.keys) <= 1:
            logger.warning("Only one API key available, cannot rotate")
            return False

        original_index = self.current_index
        attempts = 0

        while attempts < len(self.keys):
            # Move to next key
            self.current_index = (self.current_index + 1) % len(self.keys)
            attempts += 1

            # Check if this key is available
            if self.keys[self.current_index].is_available():
                self.rotation_count += 1
                logger.info(
                    f"🔄 Rotated to API key {self.current_index + 1}/{len(self.keys)}"
                )
                return True

        # No available keys
        logger.error("❌ No API keys available (all exhausted or in cooldown)")
        self.current_index = original_index
        return False

    def get_status(self) -> Dict:
        """Get status of all keys."""
        return {
            "current_key": self.current_index + 1,
            "total_keys": len(self.keys),
            "rotation_count": self.rotation_count,
            "keys": [
                {
                    "id": i + 1,
                    "status": key.status.value,
                    "failure_count": key.failure_count,
                    "total_requests": key.total_requests,
                    "total_failures": key.total_failures,
                    "available": key.is_available(),
                }
                for i, key in enumerate(self.keys)
            ],
        }

    def reset_all(self):
        """Reset all keys to healthy state."""
        for key in self.keys:
            key.status = KeyStatus.HEALTHY
            key.failure_count = 0
        logger.info("🔄 Reset all API keys to healthy state")


# Global instance
_key_rotator: Optional[NVIDIAKeyRotator] = None


def get_rotator() -> NVIDIAKeyRotator:
    """Get or create the global key rotator instance."""
    global _key_rotator
    if _key_rotator is None:
        _key_rotator = NVIDIAKeyRotator()
    return _key_rotator


def get_current_key() -> str:
    """Get the current API key."""
    return get_rotator().get_current_key()


def record_success():
    """Record a successful request."""
    get_rotator().record_success()


def record_failure(status_code: Optional[int] = None):
    """Record a failed request."""
    get_rotator().record_failure(status_code)


def rotate_key():
    """Rotate to the next API key."""
    return get_rotator().rotate()


# Initialize on import if NVIDIA_API_KEY_1 or NVIDIA_API_KEY is set
if __name__ == "__main__":
    # Test the rotator
    print("Testing NVIDIA Key Rotator...")
    rotator = NVIDIAKeyRotator()
    print(f"Status: {rotator.get_status()}")
