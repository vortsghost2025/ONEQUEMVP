# OneQueue Safety Phase 1 - Implementation Plan

**Date**: 2026-04-09  
**Status**: Ready for implementation  
**Priority**: CRITICAL SAFETY  
**Estimated Time**: 90 minutes  
**Risk Reduction**: 80%

---

## Context for GLM

You are about to implement **Phase 1: Critical Safety Features** from the FORTRESS architecture analysis. This is based on battle-tested patterns from a production trading bot that survived 19 emergency debugging sessions.

**Current State**:
- ✅ OneQueue running on VPS (187.77.3.56)
- ✅ Pre-flight checks already implemented
- ✅ Service monitor running (60s checks)
- ⚠️ LSP errors in `app/api/router_api.py` (non-blocking)
- ⚠️ Using basic retry logic (needs enhancement with tenacity)

**What NOT to touch**:
- ❌ Don't change existing preflight.py (already working)
- ❌ Don't modify service_monitor.py (already working)
- ❌ Don't fix LSP errors in router_api.py (out of scope for this phase)

---

## Implementation Checklist

### 1. Atomic File Writes (30 min)
**File**: `app/utils/safe_io.py` (CREATE NEW)

```python
"""
Safe file I/O utilities with atomic writes and UTF-8 safety.
Prevents state corruption from power failures and encoding errors.
"""
import json
import tempfile
import os
from pathlib import Path
from typing import Any, Optional

def atomic_write_json(filepath: str, data: Any) -> bool:
    """
    Write JSON atomically to prevent corruption from power failure.
    
    Uses temp file + rename pattern which is atomic on most filesystems.
    If power fails during write, original file remains intact.
    
    Args:
        filepath: Path to JSON file
        data: Data to serialize as JSON
        
    Returns:
        True if successful, False on error
    """
    try:
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(filepath),
            prefix='.tmp_',
            suffix='.json'
        )
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (works on Windows/Linux)
            os.replace(tmp_path, filepath)
            return True
        except Exception:
            # Clean up temp file on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    except Exception as e:
        # Log error but don't crash
        print(f"⚠️ Atomic write failed for {filepath}: {e}")
        return False

def safe_read_json(filepath: str, default: Optional[Any] = None) -> Any:
    """
    Read JSON with UTF-8 encoding, never crashes.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is corrupted
        
    Returns:
        JSON data or default value
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"⚠️ Corrupted JSON in {filepath}: {e}")
        # Backup corrupted file
        backup_path = f"{filepath}.corrupted"
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            print(f"📦 Backed up corrupted file to {backup_path}")
        except Exception:
            pass
        return default
    except Exception as e:
        print(f"⚠️ Error reading {filepath}: {e}")
        return default

# Usage in app:
# from app.utils.safe_io import atomic_write_json, safe_read_json
```

**Test**:
```python
# Test atomic write
from app.utils.safe_io import atomic_write_json, safe_read_json

# Test 1: Basic write/read
test_data = {"test": "data", "number": 42}
success = atomic_write_json("data/test.json", test_data)
assert success, "Write failed"

# Test 2: Read back
read_data = safe_read_json("data/test.json")
assert read_data == test_data, "Data mismatch"

# Test 3: Missing file with default
missing = safe_read_json("data/missing.json", default={"default": True})
assert missing["default"] == True, "Default not returned"

print("✅ All atomic write tests passed")
```

---

### 2. Error Recovery Manager (45 min)
**File**: `app/services/error_recovery.py` (CREATE NEW)

```python
"""
Error recovery manager with retry logic and circuit breaker pattern.
Based on FORTRESS production patterns.
"""
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from functools import wraps
import time
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ErrorRecoveryManager:
    """
    Manages error recovery with exponential backoff and circuit breaker.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.failure_counts = {}
        self.circuit_open = {}
        self.circuit_open_time = {}
    
    def retry_decorator(self, exception_types: tuple = (Exception,)):
        """
        Decorator for automatic retry with exponential backoff.
        
        Usage:
            @error_manager.retry_decorator((ConnectionError, TimeoutError))
            def api_call():
                pass
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            @retry(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=self.base_delay, max=self.max_delay),
                retry=retry_if_exception_type(exception_types),
                reraise=True
            )
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def is_transient_error(self, error: Exception) -> bool:
        """
        Check if error is transient (should retry) or fatal (should not retry).
        """
        transient_indicators = [
            "timeout", "rate_limit", "network", "connection",
            "503", "429", "502", "temporary", "transient"
        ]
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in transient_indicators)
    
    def should_retry(self, error_key: str) -> bool:
        """
        Check if should retry based on error history.
        """
        if error_key not in self.failure_counts:
            return True
        
        return self.failure_counts[error_key] < self.max_retries
    
    def record_failure(self, error_key: str):
        """
        Record a failure for tracking.
        """
        self.failure_counts[error_key] = self.failure_counts.get(error_key, 0) + 1
    
    def record_success(self, error_key: str):
        """
        Record a success, reset failure count.
        """
        if error_key in self.failure_counts:
            del self.failure_counts[error_key]
    
    def circuit_breaker(self, resource: str, threshold: int = 5, timeout: int = 300) -> bool:
        """
        Circuit breaker pattern - stops requests to failing resources.
        
        Returns True if circuit is OPEN (should NOT make request)
        Returns False if circuit is CLOSED (can make request)
        """
        current_time = time.time()
        
        # Check if circuit is open
        if resource in self.circuit_open and self.circuit_open[resource]:
            # Check if timeout has passed
            if current_time - self.circuit_open_time.get(resource, 0) > timeout:
                # Reset circuit
                self.circuit_open[resource] = False
                return False
            else:
                return True  # Circuit still open
        
        return False  # Circuit closed
    
    def open_circuit(self, resource: str):
        """
        Open circuit for a resource (stop sending requests).
        """
        self.circuit_open[resource] = True
        self.circuit_open_time[resource] = time.time()
        logger.warning(f"⚠️ Circuit breaker OPEN for {resource}")
    
    def close_circuit(self, resource: str):
        """
        Close circuit for a resource (resume sending requests).
        """
        self.circuit_open[resource] = False
        logger.info(f"✅ Circuit breaker CLOSED for {resource}")

# Global instance
error_recovery = ErrorRecoveryManager()

# Convenience decorators
def nvidia_api_retry(func: Callable) -> Callable:
    """Retry decorator for NVIDIA API calls."""
    @wraps(func)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def ollama_retry(func: Callable) -> Callable:
    """Retry decorator for Ollama API calls."""
    @wraps(func)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

**Usage Example**:
```python
# In app/services/nvidia_service.py
from app.services.error_recovery import nvidia_api_retry, error_recovery

class NvidiaService:
    @nvidia_api_retry
    def generate_completion(self, prompt: str):
        # This will automatically retry on connection errors
        response = requests.post(API_URL, json={"prompt": prompt})
        return response.json()
    
    def safe_call(self, prompt: str):
        """Manual circuit breaker example."""
        if error_recovery.circuit_breaker("nvidia_api"):
            raise Exception("Circuit breaker open for NVIDIA API")
        
        try:
            result = self.generate_completion(prompt)
            error_recovery.close_circuit("nvidia_api")
            return result
        except Exception as e:
            error_recovery.open_circuit("nvidia_api")
            raise
```

**Requirements Update**:
```txt
# requirements.txt - ADD THIS
tenacity>=8.2.0
```

---

### 3. Graceful Shutdown (15 min)
**File**: `app/services/graceful_shutdown.py` (CREATE NEW)

```python
"""
Graceful shutdown handler with signal handlers and cleanup.
Ensures clean shutdown on SIGINT, SIGTERM, or exit.
"""
import signal
import sys
import atexit
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)

class GracefulShutdown:
    """
    Manages graceful shutdown with cleanup handlers.
    """
    
    def __init__(self):
        self.cleanup_handlers: List[Callable] = []
        self.is_shutting_down = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Register atexit handler
        atexit.register(self._cleanup)
    
    def _signal_handler(self, signum, frame):
        """Handle SIGINT and SIGTERM."""
        if self.is_shutting_down:
            logger.warning("⚠️ Second signal received, forcing shutdown...")
            sys.exit(1)
        
        self.is_shutting_down = True
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown()
        sys.exit(0)
    
    def _cleanup(self):
        """Run all cleanup handlers."""
        logger.info("🧹 Running cleanup handlers...")
        for handler in reversed(self.cleanup_handlers):
            try:
                handler()
            except Exception as e:
                logger.error(f"❌ Cleanup handler failed: {e}")
    
    def register_cleanup(self, handler: Callable):
        """
        Register a cleanup handler to run on shutdown.
        
        Usage:
            shutdown_manager.register_cleanup(lambda: db.close())
        """
        self.cleanup_handlers.append(handler)
    
    def shutdown(self):
        """
        Initiate graceful shutdown.
        """
        logger.info("🛑 Graceful shutdown initiated...")
        
        # Run cleanup
        self._cleanup()
        
        logger.info("✅ Graceful shutdown complete")

# Global instance
shutdown_manager = GracefulShutdown()

# Usage in app/main.py:
# from app.services.graceful_shutdown import shutdown_manager
# 
# # Register cleanup handlers
# shutdown_manager.register_cleanup(lambda: database.close())
# shutdown_manager.register_cleanup(lambda: worker.stop())
# shutdown_manager.register_cleanup(lambda: logger.info("Shutting down..."))
```

**Usage in FastAPI**:
```python
# In app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.graceful_shutdown import shutdown_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("✅ Starting up...")
    yield
    # Shutdown (automatic)
    logger.info("🛑 FastAPI shutdown...")

app = FastAPI(lifespan=lifespan)

# Register cleanup
shutdown_manager.register_cleanup(lambda: logger.info("Closing database..."))
```

---

## Testing Plan

### Test 1: Atomic Writes (5 min)
```bash
cd S:\TAKE10
python -c "
from app.utils.safe_io import atomic_write_json, safe_read_json
import json

# Test 1: Basic write/read
test_data = {'test': 'data', 'number': 42}
success = atomic_write_json('data/test_atomic.json', test_data)
assert success, 'Write failed'

read_data = safe_read_json('data/test_atomic.json')
assert read_data == test_data, 'Data mismatch'

# Test 2: Missing file with default
missing = safe_read_json('data/missing.json', default={'default': True})
assert missing['default'] == True

# Cleanup
import os
if os.path.exists('data/test_atomic.json'):
    os.remove('data/test_atomic.json')

print('✅ All atomic write tests passed')
"
```

### Test 2: Error Recovery (5 min)
```bash
cd S:\TAKE10
python -c "
from app.services.error_recovery import error_recovery, nvidia_api_retry
import time

# Test circuit breaker
assert error_recovery.circuit_breaker('test') == False, 'Circuit should be closed'

error_recovery.open_circuit('test')
assert error_recovery.circuit_breaker('test') == True, 'Circuit should be open'

error_recovery.close_circuit('test')
assert error_recovery.circuit_breaker('test') == False, 'Circuit should be closed'

print('✅ Error recovery tests passed')
"
```

### Test 3: Graceful Shutdown (5 min)
```bash
cd S:\TAKE10
python -c "
from app.services.graceful_shutdown import shutdown_manager

cleanup_called = False

def test_cleanup():
    global cleanup_called
    cleanup_called = True
    print('Cleanup handler called')

shutdown_manager.register_cleanup(test_cleanup)
shutdown_manager.shutdown()

assert cleanup_called, 'Cleanup handler should be called'
print('✅ Graceful shutdown tests passed')
"
```

---

## Files to Create

1. `app/utils/safe_io.py` - Atomic file I/O
2. `app/services/error_recovery.py` - Error recovery manager
3. `app/services/graceful_shutdown.py` - Graceful shutdown handler

## Files to Modify

1. `requirements.txt` - Add `tenacity>=8.2.0`
2. `app/main.py` - Import and use graceful shutdown
3. Existing services - Apply `@nvidia_api_retry` decorator

## Verification

After implementation:
- [ ] All tests pass
- [ ] No import errors
- [ ] LSP errors in router_api.py still present (expected, out of scope)
- [ ] Pre-flight checks still work
- [ ] Service monitor still running

---

## Next Steps (Phase 2)

After Phase 1 is complete and tested:
1. Operation Auditor
2. Metrics Collector  
3. Cleanup Scheduler

**DO NOT IMPLEMENT YET** - Wait for Phase 1 to stabilize first.

---

## Questions for GLM

1. Should we test atomic writes on the actual database file or a test file first?
2. Do you want me to apply the `@nvidia_api_retry` decorator to existing NVIDIA calls now or in a separate commit?
3. Should we create a separate branch for Phase 1 or work on main?

---

**Ready for implementation when you are!** 🚀
