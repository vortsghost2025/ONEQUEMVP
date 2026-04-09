# ONEQUEUE - Next Steps & Improvements

## Current Status: WORKING ✅
- Backend: Running on port 8081
- Frontend: Running on port 5173  
- Ollama: Running on port 9001
- NVIDIA API: Connected (189 models available)
- Task Queue: Processing successfully
- Database: Working with 20+ tasks tracked

## Priority TODO List

### 1. WORKER NVIDIA INTEGRATION (High Priority)
**Problem:** Worker only supports Ollama, not NVIDIA models
**Solution:** 
- Modify `app/worker.py` to detect NVIDIA models (starts with `meta/`, `deepseek-ai/`, etc.)
- Route NVIDIA models to `NvidiaAPI.generate()` instead of Ollama
- Add fallback chain: Local Ollama → NVIDIA Cloud

**Files to modify:**
- `app/worker.py` (lines 120-125)
- `app/services/nvidia_api.py` (add sync wrapper or use async)

**Test:** Create task with model `meta/llama-4-maverick-17b-128e-instruct` should process via NVIDIA API

---

### 2. OLLAMA MODEL SELECTION UI (Medium Priority)
**Problem:** Frontend doesn't show available Ollama models
**Solution:**
- Add `/ollama/models` endpoint in backend
- Fetch Ollama models in frontend
- Show dropdown with both Ollama + NVIDIA models in Create Task form

**Files to modify:**
- `app/api/ollama.py` (new file)
- `frontend/src/App.jsx` (model dropdown in Create Task tab)
- `frontend/src/api.js` (add `getOllamaModels()`)

**Test:** Dropdown shows both `llama3:latest` (Ollama) and `meta/llama-4-maverick-17b-128e-instruct` (NVIDIA)

---

### 3. HEALTH DASHBOARD IN UI (Medium Priority)
**Problem:** Health status only visible via API endpoint
**Solution:**
- Add health status widget in header showing:
  - Backend: ✅ healthy
  - Ollama: ✅ healthy (port 9001)
  - NVIDIA: ✅ configured
- Poll `/queue/health` every 10 seconds
- Show warning if any service goes down

**Files to modify:**
- `frontend/src/App.jsx` (add health indicators to header)
- `frontend/src/api.js` (add `getSystemHealth()`)

**Test:** Header shows real-time status of all services

---

### 4. MODEL BENCHMARK SYSTEM (Future)
**Goal:** Auto-benchmark models for speed/quality
**Implementation:**
- Create benchmark endpoint: `/nvidia/benchmark`
- Test models with standard prompts
- Store benchmarks in database
- Show model performance in UI

**Models to benchmark:**
1. meta/llama-4-maverick-17b-128e-instruct (flagship)
2. deepseek-ai/deepseek-v3.2 (reasoning)
3. qwen/qwen3-coder-480b-a35b-instruct (coding)
4. nvidia/llama-3.3-nemotron-super-49b-v1.5 (general)

---

### 5. SMART MODEL ROUTING (Future)
**Goal:** Auto-select best model based on task type
**Implementation:**
- Detect task type from prompt:
  - Contains "code" → Qwen Coder 480B
  - Contains "reason" → DeepSeek V3.2
  - Contains "math" → DeepSeek R1
  - Long prompt → Llama 3.1 405B
  - Default → Llama 4 Maverick
- Add routing logic in worker

**Files to modify:**
- `app/services/model_router.py` (new file)
- `app/worker.py` (use router to select model)

---

### 6. UNIVERSAL INFERENCE PROXY (Future)
**Goal:** Make OneQueue work like OpenAI API
**Implementation:**
- Create `/v1/chat/completions` endpoint (OpenAI-compatible)
- Route to Ollama or NVIDIA based on model name
- Allow other apps to use OneQueue as inference proxy

**Use cases:**
- Kilo nodes can call OneQueue instead of direct API
- OpenCode can use OneQueue as universal backend
- Standardize on OpenAI API format

---

### 7. NVIDA DEVELOPER FEATURES (Your Ideas)
**Your NVIDIA RTX 5060 + Developer Account gives:**
- Free access to 189 models
- Priority inference
- Advanced models (405B, 675B parameters)

**Potential integrations:**
- Build model-switching agent
- Create fallback chain (Llama → DeepSeek → Nemotron)
- Wrap into Kilo/OpenCode as universal inference router
- Local proxy for NVIDIA API calls

---

## Testing Status

### Working ✅
- [x] Backend health endpoint
- [x] Ollama integration (port 9001)
- [x] NVIDIA API connection
- [x] Task queue processing
- [x] Frontend UI loads
- [x] All 4 tabs functional
- [x] NVIDIA models in UI (10 curated)
- [x] Task creation form
- [x] Settings persistence
- [x] Database tracking
- [x] CORS configuration
- [x] Git repo synced

### Not Working ❌
- [ ] Worker routing to NVIDIA models
- [ ] Ollama model dropdown
- [ ] Health status in UI
- [ ] Model benchmarking
- [ ] Smart routing
- [ ] OpenAI-compatible API

---

## Port Configuration (Reference)
- **Backend:** 8081 (FastAPI/Uvicorn)
- **Frontend:** 5173 (Vite/React)
- **Ollama:** 9001 (User's custom port)
- **Database:** SQLite at `./data/onequeue.db`

---

## Environment Variables
```env
OLLAMA_BASE_URL=http://localhost:9001
DATABASE_URL=sqlite:///./data/onequeue.db
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=1.0
NVIDIA_API_KEY=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
```

---

## NVIDIA Models Available (10 Curated)
1. meta/llama-4-maverick-17b-128e-instruct (flagship)
2. meta/llama-4-scout-17b-16e-instruct (flagship)
3. deepseek-ai/deepseek-v3.2 (flagship, reasoning)
4. nvidia/llama-3.3-nemotron-super-49b-v1.5 (flagship)
5. meta/llama-3.1-405b-instruct (flagship)
6. mistralai/mistral-large-3-675b-instruct-2512 (flagship)
7. google/gemma-4-31b-it (fast)
8. microsoft/phi-4-mini-instruct (fast)
9. qwen/qwen3-coder-480b-a35b-instruct (coding)
10. deepseek-ai/deepseek-r1-distill-llama-8b (reasoning)

Plus 179 more models available via NVIDIA API.

---

## Next Agent Instructions
1. Read this file first to understand current state
2. Check system health: `curl http://localhost:8081/queue/health`
3. Pick ONE priority from TODO list above
4. Test thoroughly with Playwright before committing
5. Update this file after completing tasks

---

**Repository:** https://github.com/vortsghost2025/ONEQUEMVP.git
**Last Commit:** f47fd63 - "Add NVIDIA NIM API integration with 189 enterprise models"
