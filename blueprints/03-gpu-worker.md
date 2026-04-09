# Blueprint 03: GPU Worker Implementation

## Complete Worker Code

This is the full GPU-aware worker that integrates with your existing OneQueue system.

### File: `app/gpu_worker.py`

```python
"""
GPU-Accelerated Worker for OneQueue
Single agent that outperforms 5 CPU agents
Uses RTX 5060 (sm_89) for batch processing
"""

import asyncio
import threading
import time
import logging
from typing import List, Optional
from sqlmodel import Session, select

from app.utils import engine, logger
from cuda.cuda_interface import get_gpu_processor

# How many tasks to grab per GPU batch
BATCH_SIZE = 50
# How often to check for new tasks (seconds)
POLL_INTERVAL = 0.1
# Max concurrent GPU operations
MAX_GPU_CONCURRENT = 4


class GPUWorker:
    """
    Single GPU-backed worker that replaces 5 CPU agents

    Pipeline:
    1. Fetch batch of pending tasks from SQLite
    2. GPU: Deduplicate near-identical tasks
    3. GPU: Score and prioritize tasks
    4. Execute tasks (CPU for I/O, GPU for compute)
    5. Update status in SQLite
    """

    def __init__(self):
        self.gpu = get_gpu_processor()
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.stats = {
            "tasks_processed": 0,
            "tasks_deduplicated": 0,
            "batches_processed": 0,
            "total_gpu_time_ms": 0.0,
            "errors": 0,
        }
        logger.info(f"GPUWorker initialized - {self.gpu.gpu_name}")

    def start(self):
        """Start the GPU worker in a background thread"""
        self.running = True
        self._thread = threading.Thread(
            target=self._run_event_loop,
            name="gpu-worker",
            daemon=True
        )
        self._thread.start()
        logger.info("GPUWorker started")

    def stop(self):
        """Graceful shutdown"""
        logger.info("GPUWorker stopping...")
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("GPUWorker stopped")

    def _run_event_loop(self):
        """Run async event loop in worker thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main_loop())

    async def _main_loop(self):
        """Main processing loop"""
        logger.info("GPUWorker main loop started")

        while self.running:
            try:
                # Fetch pending tasks
                tasks = self._fetch_pending_tasks(BATCH_SIZE)

                if not tasks:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                # Process batch on GPU
                t0 = time.perf_counter()
                await self._process_batch(tasks)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                self.stats["batches_processed"] += 1
                self.stats["total_gpu_time_ms"] += elapsed_ms

                logger.debug(
                    f"Batch processed: {len(tasks)} tasks in {elapsed_ms:.1f}ms"
                )

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"GPUWorker error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error

    def _fetch_pending_tasks(self, limit: int) -> List[dict]:
        """Fetch pending tasks from SQLite"""
        try:
            with Session(engine) as session:
                # Import your Task model here
                from app.models import Task  # adjust import

                tasks = session.exec(
                    select(Task)
                    .where(Task.status == "pending")
                    .limit(limit)
                ).all()

                # Mark as running
                task_dicts = []
                for task in tasks:
                    task.status = "running"
                    session.add(task)
                    task_dicts.append({
                        "id": task.id,
                        "payload": task.payload,
                        "priority": getattr(task, 'priority', 5),
                        "created_at": task.created_at,
                    })

                session.commit()
                return task_dicts

        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            return []

    async def _process_batch(self, tasks: List[dict]):
        """
        GPU-accelerated batch processing pipeline
        """
        original_count = len(tasks)

        # Step 1: GPU deduplication
        unique_tasks = await self.gpu.deduplicate_tasks(tasks, threshold=0.95)
        deduped = original_count - len(unique_tasks)
        self.stats["tasks_deduplicated"] += deduped

        # Step 2: GPU priority scoring
        prioritized = await self.gpu.prioritize_queue(unique_tasks)

        # Step 3: Execute tasks (async, up to MAX_GPU_CONCURRENT at once)
        semaphore = asyncio.Semaphore(MAX_GPU_CONCURRENT)

        async def run_with_semaphore(task):
            async with semaphore:
                return await self._execute_task(task)

        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in prioritized],
            return_exceptions=True
        )

        # Step 4: Update results in DB
        self._update_task_results(prioritized, results)
        self.stats["tasks_processed"] += len(prioritized)

    async def _execute_task(self, task: dict) -> dict:
        """
        Execute a single task
        Replace this with your actual task logic
        """
        task_id = task.get("id")
        payload = task.get("payload", {})

        # Route to appropriate handler
        task_type = payload.get("type", "default") if isinstance(payload, dict) else "default"

        handlers = {
            "ollama_inference": self._handle_ollama_task,
            "batch_compute": self._handle_gpu_compute_task,
            "default": self._handle_default_task,
        }

        handler = handlers.get(task_type, handlers["default"])
        return await handler(task)

    async def _handle_ollama_task(self, task: dict) -> dict:
        """
        Ollama inference task - GPU already handles this
        Just need to make the API call
        """
        import aiohttp

        payload = task.get("payload", {})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": payload.get("model", "llama3"),
                    "prompt": payload.get("prompt", ""),
                    "stream": False,
                }
            ) as resp:
                result = await resp.json()
                return {
                    "task_id": task["id"],
                    "status": "completed",
                    "result": result.get("response", ""),
                }

    async def _handle_gpu_compute_task(self, task: dict) -> dict:
        """GPU compute task - uses your RTX 5060 kernels"""
        payload = task.get("payload", {})
        data = payload.get("data", [])

        if data and self.gpu.cuda_available:
            import cupy as cp
            import numpy as np

            # Run on GPU
            gpu_data = cp.asarray(np.array(data, dtype=np.float32))
            result = cp.sum(gpu_data ** 2)
            return {
                "task_id": task["id"],
                "status": "completed",
                "result": float(result.get()),
            }

        return {"task_id": task["id"], "status": "completed", "result": sum(data)}

    async def _handle_default_task(self, task: dict) -> dict:
        """Default task handler"""
        await asyncio.sleep(0.01)  # Simulate work
        return {"task_id": task["id"], "status": "completed", "result": "ok"}

    def _update_task_results(self, tasks: List[dict], results: list):
        """Write results back to SQLite"""
        try:
            with Session(engine) as session:
                from app.models import Task

                for task, result in zip(tasks, results):
                    db_task = session.get(Task, task["id"])
                    if db_task:
                        if isinstance(result, Exception):
                            db_task.status = "failed"
                            db_task.result = str(result)
                        else:
                            db_task.status = "completed"
                            db_task.result = str(result)
                        session.add(db_task)

                session.commit()
        except Exception as e:
            logger.error(f"Failed to update results: {e}")

    def get_stats(self) -> dict:
        """Get worker performance stats"""
        stats = dict(self.stats)
        stats["gpu_stats"] = self.gpu.get_gpu_stats()

        if stats["batches_processed"] > 0:
            stats["avg_batch_time_ms"] = (
                stats["total_gpu_time_ms"] / stats["batches_processed"]
            )

        return stats
```

---

## Integration with FastAPI

### File: `app/main.py` (Additions)

```python
from app.gpu_worker import GPUWorker
from cuda.cuda_interface import get_gpu_processor

# Global GPU worker
gpu_worker: GPUWorker = None

@app.on_event("startup")
async def startup_event():
    global gpu_worker
    gpu_worker = GPUWorker()
    gpu_worker.start()
    logger.info("GPU Worker started on startup")

@app.on_event("shutdown")
async def shutdown_event():
    if gpu_worker:
        gpu_worker.stop()

# GPU stats endpoint
@app.get("/gpu/stats")
async def get_gpu_stats():
    """Real-time GPU utilization and worker stats"""
    if gpu_worker:
        return gpu_worker.get_stats()
    return {"error": "GPU worker not running"}

# GPU health check
@app.get("/gpu/health")
async def gpu_health():
    gpu = get_gpu_processor()
    stats = gpu.get_gpu_stats()
    return {
        "status": "healthy",
        "cuda_available": stats["cuda_available"],
        "gpu": stats["gpu_name"],
        "memory_used_pct": stats.get("gpu_memory_used_pct", 0),
    }
```

---

## Lifecycle Management

### Startup Sequence
```python
# 1. Application starts
app → GPUWorker.__init__() → get_gpu_processor()

# 2. GPU initialized
GPUTaskProcessor(device_id=0)
  ├─ Detect CUDA
  ├─ Load device properties
  └─ Create thread pool

# 3. Worker starts
gpu_worker.start()
  ├─ Create background thread
  ├─ Start event loop
  └─ Begin polling for tasks
```

### Shutdown Sequence
```python
# Graceful shutdown
gpu_worker.stop()
  ├─ Set running = False
  ├─ Wait for thread (10s timeout)
  ├─ Clean up event loop
  └─ Release GPU resources
```

---

## Monitoring & Metrics

### Stats Endpoint Response
```json
{
  "tasks_processed": 1250,
  "tasks_deduplicated": 340,
  "batches_processed": 25,
  "total_gpu_time_ms": 450.5,
  "errors": 0,
  "avg_batch_time_ms": 18.02,
  "gpu_stats": {
    "gpu_name": "NVIDIA GeForce RTX 5060",
    "cuda_available": true,
    "device_id": 0,
    "gpu_memory_free_mb": 7800,
    "gpu_memory_total_mb": 8192,
    "gpu_memory_used_pct": 4.8
  }
}
```

### Prometheus Metrics (Optional)
```python
from prometheus_client import Counter, Histogram, Gauge

gpu_tasks_processed = Counter('gpu_worker_tasks_total', 'Total tasks processed')
gpu_batch_time = Histogram('gpu_worker_batch_seconds', 'Batch processing time')
gpu_memory_usage = Gauge('gpu_memory_usage_percent', 'GPU memory usage')

# In worker loop
gpu_tasks_processed.inc(len(tasks))
gpu_batch_time.observe(elapsed_ms / 1000.0)
```

---

## Configuration Options

### Environment Variables
```bash
# GPU configuration
GPU_DEVICE_ID=0
GPU_BATCH_SIZE=50
GPU_MAX_CONCURRENT=4
GPU_POLL_INTERVAL=0.1

# Memory management
GPU_MEMORY_FRACTION=0.8  # Max GPU memory to use
GPU_ALLOW_GROWTH=true    # Don't pre-allocate all memory
```

### Python Configuration
```python
import os

BATCH_SIZE = int(os.getenv("GPU_BATCH_SIZE", "50"))
MAX_GPU_CONCURRENT = int(os.getenv("GPU_MAX_CONCURRENT", "4"))
POLL_INTERVAL = float(os.getenv("GPU_POLL_INTERVAL", "0.1"))
```

---

## Testing the Worker

### Unit Test
```python
import pytest
from app.gpu_worker import GPUWorker

@pytest.mark.asyncio
async def test_gpu_worker_lifecycle():
    worker = GPUWorker()
    
    # Start
    worker.start()
    await asyncio.sleep(0.1)  # Let it initialize
    
    # Should be running
    assert worker.running is True
    
    # Stop
    worker.stop()
    assert worker.running is False

@pytest.mark.asyncio
async def test_worker_processes_tasks():
    worker = GPUWorker()
    worker.start()
    
    try:
        # Submit test task
        task = {
            "id": "test-1",
            "payload": {"type": "default"},
            "priority": 5,
            "created_at": time.time()
        }
        
        await worker._process_batch([task])
        
        # Should have processed 1 task
        assert worker.stats["tasks_processed"] == 1
        
    finally:
        worker.stop()
```

### Integration Test
```python
import aiohttp
import asyncio

async def test_gpu_endpoint():
    async with aiohttp.ClientSession() as session:
        # Check GPU health
        async with session.get("http://localhost:8081/gpu/health") as resp:
            data = await resp.json()
            assert data["status"] == "healthy"
            assert data["cuda_available"] is True
        
        # Check stats
        async with session.get("http://localhost:8081/gpu/stats") as resp:
            data = await resp.json()
            assert "tasks_processed" in data
            assert "gpu_stats" in data
```

---

## Troubleshooting

### Worker Won't Start
```python
# Check CUDA availability
from cuda.cuda_interface import CUDA_AVAILABLE
print(f"CUDA available: {CUDA_AVAILABLE}")

# Check GPU initialization
try:
    gpu = get_gpu_processor()
    print(f"GPU: {gpu.gpu_name}")
except Exception as e:
    print(f"GPU init failed: {e}")
```

### High Memory Usage
```python
# Monitor GPU memory
import cupy as cp
mem_info = cp.cuda.runtime.memGetInfo()
print(f"Used: {mem_info[1] - mem_info[0]} bytes")

# Reduce batch size
BATCH_SIZE = 25  # Was 50

# Clear GPU memory cache
cp.get_default_memory_pool().free_all_blocks()
```

### Slow Processing
```python
# Profile batch processing
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

await worker._process_batch(tasks)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 slowest functions
```

---

**Next**: [Blueprint 04: CUDA Kernels](./04-cuda-kernels.md)

**Status**: Ready for Implementation  
**Last Updated**: 2026-04-09  
**Target**: RTX 5060 (sm_89)
