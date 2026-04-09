# Blueprint 05: Installation Guide

## Step-by-Step Installation

### Prerequisites
- Windows 10/11
- NVIDIA RTX 5060 (or compatible GPU)
- Python 3.9+
- Git (optional)

---

## Step 1: Install CUDA Toolkit

```powershell
# Download CUDA 13.2 from NVIDIA
# https://developer.nvidia.com/cuda-downloads

# Install to C:\NVIDIA_CUDA_Installer\
# Make sure to select:
# ✓ CUDA Toolkit
# ✓ Nsight Systems
# ✓ Nsight Compute
```

### Verify Installation
```powershell
nvcc --version
# Should show: CUDA compilation tools, release 13.2
```

---

## Step 2: Install Python Dependencies

```powershell
cd S:\TAKE10

# Install GPU packages
pip install cupy-cuda12x numba aiohttp pytest-asyncio

# Verify GPU detection
python -c "import cupy as cp; print('GPU:', cp.cuda.runtime.getDeviceProperties(0)['name'])"
```

### Expected Output
```
GPU: NVIDIA GeForce RTX 5060
```

---

## Step 3: Build CUDA Kernels

```powershell
cd S:\snac-v2\kimi-shared\cuda-compiler

# Build all kernels for RTX 5060
.\build_rtx5060.ps1
```

### Expected Output
```
========================================
RTX 5060 CUDA Build Script
Architecture: sm_89 (Blackwell)
========================================

[1/3] Building benchmarks...
✓ benchmark.exe built
[2/3] Building kernels...
✓ inference_kernel.exe built
✓ arb_kernel_graph.exe built
✓ arb_kernel_tensor.exe built
[3/3] Running benchmark...
Benchmark complete!
```

---

## Step 4: Create Project Structure

```powershell
cd S:\TAKE10

# Create directories
New-Item -ItemType Directory -Force -Path @(
    "app",
    "cuda",
    "cuda/kernels",
    "tests"
)

# Copy files from blueprints
Copy-Item "blueprints\*.md" ".\" -Force
```

---

## Step 5: Add Source Files

### Create `cuda/cuda_interface.py`
Copy from Blueprint 02

### Create `app/gpu_worker.py`
Copy from Blueprint 03

### Create `app/main.py` additions
Add GPU endpoints to existing FastAPI app

---

## Step 6: Test Installation

```powershell
# Run GPU tests
pytest tests/test_gpu_worker.py -v

# Expected output:
# test_gpu_batch_scoring PASSED
# test_deduplication PASSED
# test_priority_ordering PASSED
```

---

## Step 7: Run Application

```powershell
# Start OneQueue with GPU worker
python -m uvicorn app.main:app --host 127.0.0.1 --port 8081

# Check GPU health
curl http://localhost:8081/gpu/health

# Expected:
# {"status":"healthy","cuda_available":true,"gpu":"NVIDIA GeForce RTX 5060"}
```

---

## Troubleshooting

### CUDA Not Found
```powershell
# Add to PATH
$env:PATH = "C:\NVIDIA_CUDA_Installer\bin;$env:PATH"
```

### CuPy Import Error
```powershell
# Reinstall with correct CUDA version
pip uninstall cupy-cuda12x
pip install cupy-cuda12x --no-cache-dir
```

### GPU Not Detected
```python
from cuda.cuda_interface import CUDA_AVAILABLE
print(f"CUDA available: {CUDA_AVAILABLE}")
# If False, check CUDA installation
```

---

**Next**: [Blueprint 06: Testing](./06-testing.md)
