# OneQueue MVP Specification

## Project Overview

**Project Name:** OneQueue  
**Type:** Local-first AI workbench for solo builders  
**Core Promise:** Run local AI without frying your computer  
**Target Users:** Solo developers with limited hardware who want to run Ollama tasks safely

---

## Architecture

### Approach: Minimal REST API
- FastAPI backend + SQLite + background worker thread
- Single process architecture for simplicity
- Ollama as the only model provider
- React + Vite frontend (minimal, live-wired)

### Directory Structure

```
onequeue/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py                # AppSettings (env-based)
│   │   ├── db.py                    # Database setup
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── tasks.py             # Task CRUD
│   │   │   ├── queue.py             # Queue control
│   │   │   ├── system.py            # System stats
│   │   │   └── settings.py          # Settings CRUD
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py              # Task SQLModel
│   │   │   ├── run.py               # Run SQLModel
│   │   │   └── settings.py          # Settings SQLModel
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ollama.py            # Ollama client
│   │   │   ├── monitor.py           # System monitoring
│   │   │   ├── queue_worker.py      # Background worker
│   │   │   └── logging.py           # Logging setup
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── api.js                  # Real API client
├── data/
│   ├── onequeue.db                  # SQLite database
│   └── logs/                       # Rotated logs
├── scripts/
│   ├── reset_db.py
│   ├── seed_data.py
│   └── start_dev.py
├── docs/
│   └── specs/
└── README.md
```

---

## Data Models

### Task Model
```python
class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    prompt: str
    model: str = Field(default="llama3")
    status: str = Field(default="pending")  # pending/running/completed/failed/cancelled
    priority: int = Field(default=5)       # 1=highest, 10=lowest
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    timeout_seconds: int = Field(default=120)
    attempt_count: int = Field(default=1)  # Current attempt (starts at 1)
    max_retries: int = Field(default=2)    # Allow 2 retries (= 3 total attempts)
    cancel_requested: bool = Field(default=False)  # Cooperative cancellation flag
    output_text: str | None = None
    error_text: str | None = None
```

### Run Model (execution logging)
```python
class Run(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    attempt_number: int  # 1, 2, 3 - which attempt this run represents
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    duration_ms: int
    success: bool
    error_text: str | None = None  # Error message if failed
    token_estimate: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Settings Model (runtime-editable)
```python
class Settings(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    max_ram_percent: float = Field(default=85.0)
    max_cpu_percent: float = Field(default=90.0)
    max_disk_percent: float = Field(default=90.0)
    auto_pause: bool = Field(default=True)
    default_model: str = Field(default="llama3")
    default_timeout_seconds: int = Field(default=120)
    queue_paused: bool = Field(default=False)  # ONLY for manual pause
```

### Status Enum
```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # NOTE: No PAUSED status - tasks don't pause, the queue pauses
```

---

## API Endpoints

### Tasks API (`/api/tasks`)
| Method | Endpoint | Query Params | Description |
|--------|----------|--------------|-------------|
| `POST` | `/tasks` | - | Create new task |
| `GET` | `/tasks` | `status`, `limit` | List tasks (e.g., `?status=pending&limit=50`) |
| `GET` | `/tasks/{id}` | - | Get single task |
| `PATCH` | `/tasks/{id}` | - | Partial update (title, prompt, model, priority, timeout) |
| `DELETE` | `/tasks/{id}` | - | Delete task |
| `POST` | `/tasks/{id}/cancel` | - | Cancel a task (cooperative) |
| `POST` | `/tasks/{id}/retry` | - | Retry a failed task |

### Queue API (`/api/queue`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/queue/status` | Get queue status |
| `POST` | `/queue/pause` | Pause queue (manual) |
| `POST` | `/queue/resume` | Resume queue (manual) |
| `POST` | `/queue/clear-failed` | Remove all failed tasks |

### System API (`/api/system`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/system/stats` | Get CPU%, RAM%, Disk% |
| `GET` | `/system/ollama/models` | List available Ollama models |

### Settings API (`/api/settings`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/settings` | Get current settings |
| `PUT` | `/settings` | Update settings |

### Runs API (`/api/runs`)
| Method | Endpoint | Query Params | Description |
|--------|----------|--------------|-------------|
| `GET` | `/runs` | `task_id`, `limit` | List runs (e.g., `?task_id=1&limit=100`) |

---

## Configuration

### AppSettings (from .env - bootstrap only)
```python
class AppSettings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    database_url: str = "sqlite:///./data/onequeue.db"
    polling_interval_seconds: float = 1.0
    log_level: str = "INFO"
    ollama_healthcheck_timeout_seconds: float = 5.0
    worker_shutdown_grace_seconds: int = 10
    
    class Config:
        env_file = ".env"
```

### Settings Precedence
- `.env` seeds defaults on first startup
- Runtime behavior is read from SQLite Settings table
- Database values take precedence for user-adjustable settings
- `.env` continues to control bootstrap-only values

### Logging
- Console output (stdout)
- Optional file logging to `data/logs/onequeue.log`
- TimedRotatingFileHandler (midnight rotation, 7 days retention)
- Log all: task executions, threshold events, pause/resume actions

---

## Services

### MonitorService
```python
class MonitorService:
    def get_system_stats() -> SystemStats:
        # Returns: { cpu_percent, ram_percent, disk_percent, timestamp }
    
    def check_thresholds(settings: Settings) -> ThresholdCheckResult:
        # Returns: { can_run: bool, reasons: List[str] }
```

### OllamaService
```python
class OllamaService:
    def list_models() -> List[OllamaModel]
    def generate(prompt: str, model: str, timeout: int) -> GenerateResult
    def check_health() -> bool
```

### QueueWorker (background loop)
```python
async def worker_loop():
    while True:
        # 1. Check if manually paused (settings.queue_paused)
        # 2. Check system thresholds - skip execution if exceeded, DON'T change queue_paused
        # 3. Health check Ollama - skip execution if down, DON'T change queue_paused
        # 4. Find next pending task (priority order, then created_at)
        # 5. Check cancel_requested flag - cancel if true
        # 6. Execute with timeout enforcement
        # 7. Log Run record with attempt_number, error_text
        # 8. Handle retries if under max_retries
        # 9. Sleep between iterations
```

### Worker Behaviors - CRITICAL CORRECTIONS

**1. Retry behavior:**
- When a task fails and attempt_count <= max_retries + 1:
  - Increment task.attempt_count
  - Reset task.status to "pending"
  - Clear task.started_at and task.finished_at
  - Keep task.error_text from previous attempt (append attempt info)
  
