# Critical Fixes Implementation Guide

## P0-1: Fix Hardcoded Disk Path ✅ COMPLETED

**File**: `app/services/monitor.py:29`

### Problem
```python
disk = psutil.disk_usage("C:\\").percent  # Windows only!
```

### Solution Applied
```python
def _get_disk_path() -> str:
    """Get appropriate disk path for current OS."""
    system = platform.system().lower()
    if system == 'windows':
        return 'C:\\'
    return '/'

# Then use:
disk_path = _get_disk_path()
disk = psutil.disk_usage(disk_path).percent
```

### Status: ✅ FIXED
- Added cross-platform disk path detection
- Works on Windows, Linux, and macOS

---

## P0-2: Resource Metrics Timing

**File**: `app/worker.py:76-78`

### Problem
```python
# Metrics captured AFTER task completes
cpu_percent=psutil.cpu_percent(),
ram_percent=psutil.virtual_memory().percent,
disk_percent=psutil.disk_usage("C:\\").percent,
```

This doesn't reflect actual resource usage DURING inference.

### Solution
```python
# Capture BEFORE execution
cpu_before = psutil.cpu_percent()
ram_before = psutil.virtual_memory().percent
disk_path = _get_disk_path()
disk_before = psutil.disk_usage(disk_path).percent

try:
    # ... execute task ...
    success = True
except Exception as e:
    error_text = str(e)

# Capture AFTER execution  
cpu_after = psutil.cpu_percent()
ram_after = psutil.virtual_memory().percent
disk_after = psutil.disk_usage(disk_path).percent

# Use max for safety (captures peak usage)
run = Run(
    task_id=task.id,
    cpu_percent=max(cpu_before, cpu_after),
    ram_percent=max(ram_before, ram_after),
    disk_percent=max(disk_before, disk_after),
    # ...
)
```

### Implementation Steps
1. Add `_get_disk_path()` helper to worker.py
2. Capture metrics before task execution
3. Capture metrics after task execution  
4. Store max values in Run record

---

## P0-3: API Key Validation at Startup

**File**: `app/services/nvidia_api.py`

### Problem
No validation of API key before use, leading to confusing runtime errors.

### Solution
Add validation in `NvidiaAPI.__init__()`:

```python
class NvidiaAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.nvidia_api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"
        
        # Validate API key format
        if not self.api_key:
            raise ValueError(
                "NVIDIA API key is required. "
                "Set NVIDIA_API_KEY environment variable or pass api_key parameter."
            )
        
        # Optional: Validate key format (NVIDIA keys start with 'nvapi-')
        if not self.api_key.startswith('nvapi-'):
            logger.warning(
                f"NVIDIA API key format looks incorrect. "
                f"Expected format: nvapi-..., got: {self.api_key[:10]}..."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
```

### Implementation Steps
1. Add `__init__` method if not exists
2. Validate API key presence
3. Validate API key format (starts with 'nvapi-')
4. Raise clear error message if invalid

---

## P1-4: Consolidate Model Detection Logic

**File**: `app/worker.py:30-41`

### Problem
Duplicate logic for detecting NVIDIA models:
```python
# worker.py duplicates SmartRouter._is_nvidia_model()
is_nvidia = any(
    task.model.startswith(prefix)
    for prefix in ["meta/", "deepseek-ai/", "nvidia/", "qwen/", "google/", "microsoft/", "mistralai/"]
)
```

### Solution
Use the existing `SmartRouter` class:

```python
# At module level
smart_router = SmartRouter()

def _is_nvidia_model(model_id: str) -> bool:
    """Check if model is from NVIDIA using smart router logic."""
    return smart_router._is_nvidia_model(model_id)

# Then in execute_task:
is_nvidia = _is_nvidia_model(task.model)
```

### Benefits
- Single source of truth
- Easier to maintain
- Consistent behavior
- Supports new providers automatically

---

## P1-5: Standardize Status Enum Usage

**Files**: Multiple

### Problem
Inconsistent use of string literals vs enums:
```python
# worker.py:188
.where(Task.status == "pending")  # String literal

# queue.py:25-26  
if task.status == TaskStatus.PENDING:  # Enum
```

### Solution
Use enum consistently:

```python
# In Task model, ensure status is properly typed
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Then use everywhere:
from app.models import TaskStatus

# In queries:
.where(Task.status == TaskStatus.PENDING)

# In comparisons:
if task.status == TaskStatus.PENDING:
    task.status = TaskStatus.RUNNING
```

### Implementation Steps
1. Ensure TaskStatus enum exists
2. Replace all string literals with enum values
3. Update type hints
4. Add migration if needed

---

## P1-6: HTTP Connection Pooling

**Files**: `ollama.py`, `nvidia_api.py`

### Problem
Creating new client for each request:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(...)
```

### Solution
Use a shared client with connection pooling:

```python
# ollama.py
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    async def client(self) -> httpx.AsyncClient:
        if self._client is None:
            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=50,
                keepalive_expiry=30.0
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=limits,
                timeout=httpx.Timeout(30.0, connect=5.0)
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def generate(self, prompt: str, model: str, timeout: int):
        client = await self.client
        response = await client.post(...)
```

### Implementation Steps
1. Create singleton client instances
2. Configure connection pooling limits
3. Add proper cleanup on shutdown
4. Update all API calls to use shared client

---

## P1-7: Input Sanitization

**File**: `app/services/smart_router.py:278`

### Problem
Regex on unsanitized user input:
```python
if any(re.search(p, prompt_lower) for p in code_patterns):
```

### Solution
Basic sanitization before regex:

```python
def analyze_task(self, prompt: str, context_length: int = 0) -> TaskType:
    """Analyze task to determine best model type."""
    # Basic sanitization
    if not prompt or not isinstance(prompt, str):
        return TaskType.GENERAL
    
    # Truncate if extremely long (prevent ReDoS)
    max_prompt_length = 10000
    if len(prompt) > max_prompt_length:
        prompt = prompt[:max_prompt_length]
    
    prompt_lower = prompt.lower()
    
    # ... rest of analysis ...
```

### Implementation Steps
1. Validate prompt is string
2. Truncate to reasonable length
3. Sanitize before regex operations

---

## Testing Plan

### For Each Fix

1. **Unit Tests**
   - Test the specific fix
   - Test edge cases
   - Test error conditions

2. **Integration Tests**
   - Test with full system
   - Test with real API keys
   - Test with various models

3. **Regression Tests**
   - Run existing test suite
   - Verify no breaking changes
   - Check performance metrics

### Test Cases

#### Disk Path Fix
```python
def test_disk_path_cross_platform():
    assert _get_disk_path() in ['/', 'C:\\']
```

#### Resource Metrics
```python
def test_resource_metrics_during_execution():
    # Verify metrics captured during task
    pass
```

#### API Key Validation
```python
def test_api_key_validation():
    with pytest.raises(ValueError):
        NvidiaAPI(api_key="")
```

---

## Rollback Plan

If any fix causes issues:

1. **Immediate**: Revert commit
   ```bash
   git revert <commit-hash>
   ```

2. **Document**: Create bug ticket with:
   - Issue description
   - Steps to reproduce
   - Expected vs actual behavior
   - Impact assessment

3. **Fix**: Address in next iteration

---

## Timeline

| Fix | Priority | Estimated Time | Status |
|-----|----------|----------------|--------|
| Disk Path | P0 | 30 min | ✅ Done |
| Resource Metrics | P0 | 1 hour | Pending |
| API Key Validation | P0 | 45 min | Pending |
| Model Detection | P1 | 1 hour | Pending |
| Status Enums | P1 | 2 hours | Pending |
| Connection Pooling | P1 | 3 hours | Pending |
| Input Sanitization | P1 | 1 hour | Pending |

**Total Estimated Time**: 9-10 hours

---

## Success Criteria

- [ ] All P0 fixes deployed and tested
- [ ] No regression in existing functionality
- [ ] Test coverage > 80% for changed code
- [ ] Documentation updated
- [ ] Performance metrics stable or improved

---

**Status**: Ready for implementation  
**Risk**: Low (isolated changes, well-defined)  
**Impact**: High (critical fixes for production)
