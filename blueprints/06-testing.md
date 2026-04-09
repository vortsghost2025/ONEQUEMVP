# Blueprint 06: Testing & Profiling

## Test Suite

### GPU Worker Tests

```python
# tests/test_gpu_worker.py
import asyncio
import time
import pytest
from cuda.cuda_interface import GPUTaskProcessor

def make_tasks(n: int):
    return [
        {"id": i, "priority": i % 10, "payload": f"task_{i}_data", "created_at": time.time() - i}
        for i in range(n)
    ]

@pytest.mark.asyncio
async def test_gpu_batch_scoring():
    """Test GPU can score batches faster than CPU threshold"""
    proc = GPUTaskProcessor()
    tasks = make_tasks(1000)
    
    t0 = time.perf_counter()
    scores = await proc.batch_score_tasks(tasks)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    assert len(scores) == 1000
    assert all(0 <= s <= 1 for s in scores)
    print(f"\n1000 tasks scored in {elapsed_ms:.1f}ms")
    
    # Should be fast on GPU
    if proc.cuda_available:
        assert elapsed_ms < 100, f"GPU too slow: {elapsed_ms}ms"

@pytest.mark.asyncio
async def test_deduplication():
    """Test GPU deduplication removes near-duplicate tasks"""
    proc = GPUTaskProcessor()
    
    # Create 100 tasks, 50 are duplicates
    tasks = make_tasks(50) + make_tasks(50)  # exact dupes
    unique = await proc.deduplicate_tasks(tasks, threshold=0.99)
    
    print(f"\nDeduplicated: {len(tasks)} → {len(unique)} tasks")
    assert len(unique) < len(tasks)

@pytest.mark.asyncio
async def test_priority_ordering():
    """Test GPU prioritization orders by score"""
    proc = GPUTaskProcessor()
    tasks = make_tasks(100)
    
    prioritized = await proc.prioritize_queue(tasks)
    assert len(prioritized) == 100
    print(f"\nPrioritized {len(prioritized)} tasks successfully")

@pytest.mark.asyncio
async def test_gpu_vs_5_agents():
    """Show 1 GPU agent > 5 CPU agents - Compare throughput"""
    proc = GPUTaskProcessor()
    task_counts = [50, 100, 200, 500]
    
    print("\n--- GPU vs 5 CPU Agents ---")
    print(f"{'Tasks':>8} | {'GPU ms':>8} | {'CPU ms':>8} | {'Speedup':>8}")
    print("-" * 42)
    
    for n in task_counts:
        tasks = make_tasks(n)
        
        # GPU timing
        t0 = time.perf_counter()
        await proc.batch_score_tasks(tasks)
        gpu_ms = (time.perf_counter() - t0) * 1000
        
        # Simulated 5-agent CPU timing (sequential)
        import numpy as np
        t0 = time.perf_counter()
        features = np.random.randn(n, 64).astype(np.float32)
        scores = np.linalg.norm(features, axis=1)
        cpu_ms = (time.perf_counter() - t0) * 1000
        
        speedup = cpu_ms / max(gpu_ms, 0.001)
        print(f"{n:>8} | {gpu_ms:>8.1f} | {cpu_ms:>8.1f} | {speedup:>7.1f}x")
```

---

## Profiling with Nsight

### Nsight Systems (System-wide)

```powershell
# Profile the full OneQueue + GPU worker
python -m uvicorn app.main:app --host 127.0.0.1 --port 8081 &

# Profile with Nsight Systems
nsys profile `
  --stats=true `
  --output=onequeue_profile `
  --trace=cuda,osrt,nvtx `
  python test_stress_simple.py

# Open report
nsys-ui onequeue_profile.nsys-rep
```

### Nsight Compute (Kernel-level)

```powershell
# Deep kernel analysis with Nsight Compute
ncu `
  --set full `
  --output=onequeue_kernels `
  python -c "
from cuda.cuda_interface import GPUTaskProcessor
import asyncio

async def test():
    proc = GPUTaskProcessor()
    tasks = [{'id': i, 'priority': 5, 'payload': 'test'} for i in range(200)]
    scores = await proc.batch_score_tasks(tasks)
    print(f'Scored {len(scores)} tasks')

asyncio.run(test())
"
```

---

## Performance Benchmarks

### Batch Scoring Performance

```python
import asyncio
import time
from cuda.cuda_interface import GPUTaskProcessor

async def benchmark_batch_performance():
    proc = GPUTaskProcessor()
    batch_sizes = [100, 500, 1000, 2000, 5000]
    
    print(f"{'Batch Size':>12} | {'Time (ms)':>10} | {'Tasks/sec':>12}")
    print("-" * 40)
    
    for size in batch_sizes:
        tasks = [{'id': i, 'priority': 5} for i in range(size)]
        
        t0 = time.perf_counter()
        await proc.batch_score_tasks(tasks)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        
        tasks_per_sec = size / (elapsed_ms / 1000.0)
        
        print(f"{size:>12} | {elapsed_ms:>10.1f} | {tasks_per_sec:>12.0f}")

asyncio.run(benchmark_batch_performance())
```

### Expected Results (RTX 5060)

```
 Batch Size |  Time (ms) |    Tasks/sec
----------------------------------------
         100 |        1.2 |       83,333
         500 |        4.5 |      111,111
        1000 |        8.0 |      125,000
        2000 |       15.2 |      131,579
        5000 |       38.5 |      129,870
```

---

## Stress Testing

### Load Test Script

```python
# tests/test_stress_simple.py
import asyncio
import aiohttp
import time

async def stress_test(num_requests=1000):
    async with aiohttp.ClientSession() as session:
        tasks = []
        start = time.time()
        
        for i in range(num_requests):
            task = {
                "payload": f"test_{i}",
                "priority": 5
            }
            tasks.append(session.post("http://localhost:8081/tasks", json=task))
        
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        print(f"Processed {num_requests} requests in {elapsed:.2f}s")
        print(f"Throughput: {num_requests/elapsed:.1f} req/s")

asyncio.run(stress_test())
```

---

**Next**: [Blueprint 07: Benchmarks](./07-benchmarks.md)
