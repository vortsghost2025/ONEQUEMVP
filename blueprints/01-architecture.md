# Blueprint 01: Architecture Overview

## System Design for GPU-Accelerated OneQueue

### Current Architecture (CPU-Only)

```
┌─────────────────────────────────────────────┐
│ 5 SEPARATE CPU AGENTS                       │
│                                             │
│ Agent 1: [Task Scoring]    → ~50ms/batch   │
│ Agent 2: [Deduplication]   → ~30ms/batch   │
│ Agent 3: [Prioritization]  → ~20ms/batch   │
│ Agent 4: [Ollama Routing]  → ~10ms/batch   │
│ Agent 5: [Result Writing]  → ~10ms/batch   │
│                                             │
│ Total: ~120ms per batch                     │
│ Power: 5x CPU cores                         │
└─────────────────────────────────────────────┘
```

### Proposed Architecture (GPU-Accelerated)

```
┌─────────────────────────────────────────────┐
│ 1 GPU-BACKED AGENT (RTX 5060)              │
│                                             │
│ [HTTP Request]                              │
│    ↓                                        │
│ [FastAPI + SQLite Queue]                    │
│    ↓                                        │
│ [Task Router (CPU)]                         │
│    ├── Simple tasks → CPU Worker            │
│    ├── Batch tasks → GPU Worker ◀── RTX 5060│
│    ├── Inference → Ollama ────────◀── RTX 5060│
│    └── Scoring → GPU Worker ◀───────┘       │
│                                             │
│ Total: ~18ms per batch (6.7x faster)        │
│ Power: 1x GPU + minimal CPU                 │
└─────────────────────────────────────────────┘
```

---

## Component Breakdown

### What CUDA Accelerates ✅

| Component | GPU Benefit | Speedup |
|-----------|-------------|---------|
| **Batch Scoring** | Parallel L2 norm computation | 6-8x |
| **Deduplication** | Cosine similarity matrix | 50-100x |
| **Priority Ranking** | GPU-accelerated sorting | 5-7x |
| **Vector Operations** | BLAS-level parallelism | 10-50x |
| **MEV Calculations** | Custom CUDA kernels | 10-100x |

### What Stays on CPU ❌

| Component | Reason |
|-----------|--------|
| SQLite I/O | Disk-bound, not compute-bound |
| FastAPI routing | Network-bound |
| HTTP requests | I/O-bound |
| Task result writes | Database latency |

---

## Project Structure

```
onequeue/
├── app/
│   ├── main.py              # FastAPI app (existing)
│   ├── utils.py             # Utilities (existing)
│   ├── worker.py            # CPU worker (existing)
│   ├── gpu_worker.py        # GPU worker ⭐ NEW
│   └── api/
│       └── tasks.py         # Task endpoints (existing)
├── cuda/
│   ├── kernels/
│   │   ├── batch_processor.cu    ⭐ NEW
│   │   ├── vector_similarity.cu  ⭐ NEW
│   │   └── task_scorer.cu        ⭐ NEW
│   ├── build_kernels.ps1         ⭐ NEW
│   └── cuda_interface.py         ⭐ NEW - Python bridge
├── tests/
│   ├── test_gpu_worker.py        ⭐ NEW
│   └── test_stress_simple.py     # Existing
└── requirements.txt              # Updated
```

---

## Data Flow

### 1. Task Submission
```
Client → FastAPI → SQLite (pending) → GPU Worker picks up
```

### 2. GPU Processing Pipeline
```
1. Fetch batch (50 tasks) from SQLite
2. GPU: Deduplicate (remove near-duplicates)
3. GPU: Score & prioritize
4. Execute tasks (parallel GPU for compute, CPU for I/O)
5. Write results to SQLite
6. Repeat
```

### 3. Fallback Strategy
```
if CUDA available:
    Use GPU acceleration
else:
    Fall back to NumPy (CPU)
    
# Transparent to application logic
```

---

## Hardware Requirements

### Minimum
- NVIDIA GPU with CUDA compute capability 6.0+
- 4GB GPU memory
- CUDA Toolkit 12.x

### Recommended (RTX 5060)
- RTX 5060 (sm_89, 8GB)
- CUDA 13.2
- CuPy 12.x + Numba 0.57+

### Performance Expectations
| GPU | Batch Size | Time | Throughput |
|-----|-----------|------|------------|
| RTX 5060 | 1000 tasks | 8ms | 125k tasks/sec |
| RTX 4090 | 1000 tasks | 5ms | 200k tasks/sec |
| CPU (8-core) | 1000 tasks | 50ms | 20k tasks/sec |

---

## Integration Points

### Existing OneQueue Components
- ✅ FastAPI app (main.py)
- ✅ SQLite database
- ✅ Task model
- ✅ Worker thread pool

### New Components
- ⭐ GPU Task Processor (cuda_interface.py)
- ⭐ GPU Worker (gpu_worker.py)
- ⭐ CUDA kernels (.cu files)
- ⭐ Build scripts (PowerShell)

### External Dependencies
- CuPy (GPU arrays)
- Numba (CUDA JIT)
- aiohttp (async HTTP)
- pytest-asyncio (testing)

---

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CUDA version mismatch | Medium | High | Pin versions, test thoroughly |
| GPU memory exhaustion | Low | Medium | Batch size limits, monitoring |
| Driver incompatibility | Low | High | Test on target hardware early |
| Debugging complexity | High | Medium | Extensive logging, CPU fallback |

### Operational Risks
| Risk | Mitigation |
|------|------------|
| Single point of failure | CPU fallback mode |
| Performance regression | Continuous benchmarking |
| Increased complexity | Modular design, optional feature |

---

## Migration Strategy

### Phase 1: Foundation (Week 1)
- [ ] Install CUDA toolkit
- [ ] Build test kernels
- [ ] Validate GPU detection
- [ ] Run basic benchmarks

### Phase 2: Integration (Week 2)
- [ ] Implement GPUTaskProcessor
- [ ] Add to worker pool
- [ ] Test with 10% traffic
- [ ] Monitor performance

### Phase 3: Optimization (Week 3-4)
- [ ] Profile with Nsight
- [ ] Tune batch sizes
- [ ] Optimize kernel parameters
- [ ] Scale to 100% traffic

### Phase 4: Advanced (Month 2+)
- [ ] Custom MEV kernels
- [ ] Multi-GPU support
- [ ] Advanced scheduling algorithms

---

## Success Metrics

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| Batch processing time | 120ms | 20ms | 15ms |
| Tasks/second | 800 | 5000 | 10000 |
| GPU utilization | N/A | 60%+ | 80%+ |
| Error rate | <1% | <1% | <0.5% |
| Power consumption | 100W | 60W | 40W |

---

## Decision Framework

### Implement If:
- ✅ Batch operations are bottleneck
- ✅ Processing 100+ tasks/min
- ✅ Have CUDA development experience
- ✅ Can dedicate 2-4 weeks

### Wait If:
- ❌ Basic queue is unstable
- ❌ < 50 tasks/min
- ❌ No CUDA experience on team
- ❌ Pre-product-market fit

### Don't Implement If:
- ❌ Happy path is <10 tasks/min
- ❌ No GPU hardware available
- ❌ Can't tolerate any downtime
- ❌ Team bandwidth is critical

---

**Next**: [Blueprint 02: GPU Task Processor](./02-gpu-processor.md)

**Status**: Ready for Implementation  
**Last Updated**: 2026-04-09  
**Target**: RTX 5060 (sm_89)
