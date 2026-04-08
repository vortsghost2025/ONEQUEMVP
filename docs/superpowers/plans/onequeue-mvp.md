# OneQueue MVP Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Build a local-first AI task runner with queue, persistence, and safety guardrails.

**Architecture:** FastAPI + SQLite + background worker thread. Single process. Ollama for model execution. React + Vite frontend.

**Tech Stack:** Python, FastAPI, SQLModel, SQLite, psutil, httpx, React, Vite

---

## File Structure
```
backend/app/main.py, config.py, db.py
backend/app/api/tasks.py, queue.py, system.py, settings.py, runs.py
backend/app/models/task.py, run.py, settings.py
backend/app/services/ollama.py, monitor.py, queue_worker.py, logging.py
frontend/src/App.jsx, api.js, App.css
scripts/start_dev.py
```

---

## Task 1: Backend Project Setup
**Files:** backend/requirements.txt, .env.example, app/config.py

- [ ] Create requirements.txt
```txt
fastapi==0.115.0
uvicorn==0.32.0
sqlmodel==0.0.20
httpx==0.27.2
psutil==6.1.0
pydantic-settings==2.6.0
python-dotenv==1.0.1
```

- [ ] Create .env.example
```bash
OLLAMA_BASE_URL=http://localhost:11434
DATABASE_URL=sqlite:///./data/onequeue.db
POLLING_INTERVAL_SECONDS=1.0
LOG_LEVEL=INFO
```

- [ ] Create config.py
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ollama_base_url: str = "http://localhost:11434"
    database_url: str = "sqlite:///./data/onequeue.db"
    polling_interval_seconds: float = 1.0
    log_level: str = "INFO"
    ollama_healthcheck_timeout_seconds: float = 5.0
    worker_shutdown_grace_seconds: int = 10

app_settings = AppSettings()
```

- [ ] Commit: `git add backend/requirements.txt backend/.env.example backend/app/config.py && git commit -m "feat: backend setup"`
```

---

## Task 2: Database and Models
**Files:** backend/app/db.py, app/models/task.py, run.py, settings.py

- [ ] Create db.py - Creates tables, provides session
- [ ] Create task.py - Task model with all fields
- [ ] Create run.py - Run model for logging
- [ ] Create settings.py - Settings singleton
- [ ] Test: `python -c "from app.db import create_db_and_tables; create_db_and_tables()"`
- [ ] Commit

---

## Task 3: Logging Service
**Files:** backend/app/services/logging.py

- [ ] Create logging.py with console + file rotation (7 days)
- [ ] Commit

---

## Task 4: Monitor Service
**Files:** backend/app/services/monitor.py

- [ ] Create monitor.py with get_system_stats() and check_thresholds()
- [ ] Test: `python -c "from app.services.monitor import monitor_service; print(monitor_service.get_system_stats())"`
- [ ] Commit

---

## Task 5: Ollama Service
**Files:** backend/app/services/ollama.py

- [ ] Create ollama.py with check_health(), list_models(), generate()
- [ ] Test with running Ollama
- [ ] Commit

---

## Task 6: Settings API
**Files:** backend/app/api/settings.py

- [ ] Create GET /api/settings, PUT /api/settings
- [ ] Commit

---

## Task 7: Tasks API
**Files:** backend/app/api/tasks.py

- [ ] Create POST/GET/PUT/DELETE /api/tasks with filters
- [ ] Commit

---

## Task 8: Queue API
**Files:** backend/app/api/queue.py

- [ ] Create GET /queue/status, POST /pause, /resume, /cancel/{id}, /clear-failed
- [ ] Commit

---

## Task 9: System and Runs API
**Files:** backend/app/api/system.py, runs.py

- [ ] Create GET /system/stats, /system/ollama/models
- [ ] Create GET /runs with task_id and limit filters
- [ ] Commit

---

## Task 10: Queue Worker
**Files:** backend/app/services/queue_worker.py

- [ ] Create QueueWorker class with async run_loop()
- [ ] Implement: pause check, threshold check, Ollama health, task execution, timeout, retry, Run logging, graceful shutdown
- [ ] Commit

---

## Task 11: Main Application
**Files:** backend/app/main.py

- [ ] Create FastAPI app with lifespan (start/stop worker)
- [ ] Include all routers, CORS middleware
- [ ] Test startup
- [ ] Commit

---

## Task 12: Frontend
**Files:** frontend/package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx, src/App.css, src/api.js

- [ ] Create package.json, vite.config.js, index.html
- [ ] Create api.js with all real API calls (no mocks)
- [ ] Create App.jsx with: dashboard (stats, queue controls), tasks (create, list, filter), settings (edit), runs (table)
- [ ] Create App.css with basic styling
- [ ] Commit

---

## Task 13: Scripts
**Files:** scripts/start_dev.py

- [ ] Create start_dev.py to run both backend and frontend
- [ ] Commit

---

## Task 14: Integration Testing
- [ ] Start backend: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
- [ ] Test all endpoints with curl
- [ ] Start frontend: `cd frontend && npm install && npm run dev`
- [ ] Verify end-to-end works
- [ ] Commit

---

## Task 15: Progress Tracker
**Files:** PROGRESS.md

- [ ] Create PROGRESS.md with checkboxes
- [ ] Commit

---

## Plan Complete

Total 15 tasks. Execute with subagent-driven or inline execution.

Which approach?
