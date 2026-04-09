"""
Error Recovery Manager - Automatic retry with exponential backoff
Prevents crashes from transient API failures
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, Any, List
from enum import Enum
from datetime import datetime, timedelta
import httpx

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        stop_after_delay,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log,
        after_log,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logging.warning("tenacity not installed, retry logic will be basic")

logger = logging.getLogger("onequeue.error_recovery")


class ErrorCategory(Enum):
    TRANSIENT = "transient"  # Temporary, should retry
    FATAL = "fatal"  # Permanent, should not retry
    UNKNOWN = "unknown"


class ErrorRecoveryManager:
    """
    Centralized error recovery with automatic retry logic.

    Handles:
    - NVIDIA API timeouts, rate limits
    - Ollama connection errors
    - Network failures
    - Database lock errors
    """

    TRANSIENT_ERRORS = [
        "timeout",
        "timed out",
        "rate_limit",
        "rate limit",
        "429",
        "503",
        "502",
        "504",
        "connection_reset",
        "connection refused",
        "network",
        "temporary",
        "overloaded",
        "capacity",
    ]

    FATAL_ERRORS = [
        "401",  # Unauthorized
        "403",  # Forbidden
        "404",  # Not found
        "invalid_api_key",
        "authentication",
        "unauthorized",
        "forbidden",
    ]

    def __init__(self):
        self.error_history: List[dict] = []
        self.max_history = 100

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Determine if error is transient (should retry) or fatal.

        Args:
            error: Exception to categorize

        Returns:
            ErrorCategory enum
        """
        error_str = str(error).lower()

        # Check for fatal errors first
        for fatal_pattern in self.FATAL_ERRORS:
            if fatal_pattern in error_str:
                logger.error(f"Fatal error detected: {error}")
                return ErrorCategory.FATAL

        # Check for transient errors
        for transient_pattern in self.TRANSIENT_ERRORS:
            if transient_pattern in error_str:
                logger.warning(f"Transient error detected: {error}")
                return ErrorCategory.TRANSIENT

        # Default to transient for unknown errors (safer to retry)
        logger.info(f"Unknown error type, treating as transient: {error}")
        return ErrorCategory.TRANSIENT

    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            error: Exception that occurred
            attempt: Current attempt number
            max_attempts: Maximum allowed attempts

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= max_attempts:
            return False

        category = self.categorize_error(error)
        return category == ErrorCategory.TRANSIENT

    def log_error(self, error: Exception, context: Optional[dict] = None):
        """
        Log error to history for analysis.

        Args:
            error: Exception that occurred
            context: Additional context (endpoint, task_id, etc.)
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": self.categorize_error(error).value,
            "context": context or {},
        }

        self.error_history.append(entry)

        # Trim history if too long
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def get_error_stats(self) -> dict:
        """Get error statistics for monitoring."""
        if not self.error_history:
            return {"total": 0, "transient": 0, "fatal": 0}

        transient = sum(1 for e in self.error_history if e["category"] == "transient")
        fatal = sum(1 for e in self.error_history if e["category"] == "fatal")

        return {
            "total": len(self.error_history),
            "transient": transient,
            "fatal": fatal,
            "transient_rate": transient / len(self.error_history)
            if self.error_history
            else 0,
        }


# Global instance
error_manager = ErrorRecoveryManager()


def nvidia_api_retry(
    max_attempts: int = 3,
    max_delay_seconds: int = 30,
    exponential_base: float = 2,
):
    """
    Decorator for NVIDIA API calls with automatic retry.

    Args:
        max_attempts: Maximum retry attempts (default 3)
        max_delay_seconds: Maximum delay between retries (default 30s)
        exponential_base: Base for exponential backoff (default 2)

    Usage:
        @nvidia_api_retry(max_attempts=3)
        async def call_nvidia_api(prompt: str):
            # API call implementation
            pass
    """
    if TENACITY_AVAILABLE:
        return retry(
            stop=stop_after_attempt(max_attempts) | stop_after_delay(max_delay_seconds),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
            reraise=True,
        )
    else:
        # Fallback to basic retry if tenacity not available
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_error = None
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        error_manager.log_error(
                            e, {"function": func.__name__, "attempt": attempt}
                        )

                        if not error_manager.should_retry(e, attempt, max_attempts):
                            raise

                        delay = min(exponential_base**attempt, max_delay_seconds)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} after {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)

                raise last_error

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_error = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        error_manager.log_error(
                            e, {"function": func.__name__, "attempt": attempt}
                        )

                        if not error_manager.should_retry(e, attempt, max_attempts):
                            raise

                        delay = min(exponential_base**attempt, max_delay_seconds)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} after {delay}s: {e}"
                        )
                        import time

                        time.sleep(delay)

                raise last_error

            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


def ollama_retry(max_attempts: int = 3):
    """
    Decorator specifically for Ollama polling operations.

    Args:
        max_attempts: Maximum retry attempts

    Usage:
        @ollama_retry(max_attempts=5)
        async def poll_ollama_status(task_id: str):
            # Polling implementation
            pass
    """
    return nvidia_api_retry(max_attempts=max_attempts, max_delay_seconds=15)


def database_retry(max_attempts: int = 3):
    """
    Decorator for database operations with retry.

    Handles SQLite lock errors gracefully.

    Args:
        max_attempts: Maximum retry attempts

    Usage:
        @database_retry(max_attempts=5)
        def update_task_status(task_id: int, status: str):
            # Database operation
            pass
    """
    if TENACITY_AVAILABLE:
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
    else:
        return nvidia_api_retry(max_attempts=max_attempts, max_delay_seconds=5)


# Circuit breaker pattern for repeated failures
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Opens after N consecutive failures, prevents calls for cooldown period.
    """

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Record successful operation."""
        self.failures = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed operation."""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker OPEN after {self.failures} failures")

    def can_execute(self) -> bool:
        """Check if operation can execute."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if cooldown period has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.cooldown_seconds:
                    self.state = "half-open"
                    logger.info("Circuit breaker entering HALF-OPEN state")
                    return True
            return False

        # half-open state - allow one test request
        return True

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.can_execute():
                raise Exception("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.can_execute():
                raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


# Global circuit breakers for external services
nvidia_circuit_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)
ollama_circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
