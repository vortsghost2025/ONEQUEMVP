# OneQueue

A lightweight task queue system with AI model execution capabilities using Ollama.

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Ollama (if not already installed)
# https://github.com/ollama/ollama
```

### Running the Server

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Frontend

```bash
# Install frontend dependencies
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and connects to the API at `http://localhost:8000`.

## API Reference

### Tasks

#### Create Task

Create a new AI task.

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summarize this text",
    "prompt": "Write a short summary of the benefits of exercise.",
    "model": "llama3",
    "priority": 5,
    "timeout_seconds": 120
  }'
```

Response:
```json
{
  "id": 1,
  "title": "Summarize this text",
  "prompt": "Write a short summary...",
  "model": "llama3",
  "status": "pending",
  "priority": 5,
  "created_at": "2026-04-08T12:00:00",
  ...
}
```

#### Get Task

Retrieve a task by ID.

```bash
curl http://localhost:8000/tasks/1
```

#### List Tasks

List all tasks, optionally filtered by status.

```bash
# All tasks
curl http://localhost:8000/tasks

# Filter by status
curl "http://localhost:8000/tasks?status=pending"
curl "http://localhost:8000/tasks?status=completed"
```

#### Update Task

Partially update a task.

```bash
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"priority": 1}'
```

#### Cancel Task

Cancel a running or pending task.

```bash
curl -X POST http://localhost:8000/tasks/1/cancel
```

#### Retry Task

Retry a failed or cancelled task.

```bash
curl -X POST http://localhost:8000/tasks/1/retry
```

---

### Queue

#### Get Queue Status

Get current queue state.

```bash
curl http://localhost:8000/queue/status
```

Response:
```json
{
  "queue_paused": false,
  "pending_count": 5,
  "running_count": 2
}
```

#### Pause Queue

Pause task processing.

```bash
curl -X POST http://localhost:8000/queue/pause
```

#### Resume Queue

Resume task processing.

```bash
curl -X POST http://localhost:8000/queue/resume
```

#### Clear Failed Tasks

Delete all failed tasks.

```bash
curl -X POST http://localhost:8000/queue/clear-failed
```

---

### Settings

#### Get Settings

Retrieve system configuration.

```bash
curl http://localhost:8000/settings
```

Response:
```json
{
  "id": 1,
  "max_ram_percent": 95.0,
  "max_cpu_percent": 95.0,
  "max_disk_percent": 95.0,
  "auto_pause": true,
  "default_model": "llama3",
  "default_timeout_seconds": 120,
  "queue_paused": false,
  "breach_duration_seconds": 5
}
```

#### Update Settings

Modify system configuration.

```bash
curl -X PATCH http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{
    "default_model": "llama3.1",
    "auto_pause": true
  }'
```

### Configuration

Settings can also be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///onequeue.db` | Database connection |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |

---

## OpenAPI Documentation

The API is fully documented with OpenAPI/Swagger. Access the interactive docs at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI YAML**: See `openapi.yaml` in project root

---

## Task Status Values

- `pending` - Waiting to be processed
- `running` - Currently executing
- `completed` - Finished successfully
- `failed` - Finished with error
- `cancelled` - Cancelled by user

---

## Architecture

```
┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI    │
│  (React)    │     │   Backend   │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │  Database   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Worker    │
                    │  (Ollama)   │
                    └─────────────┘
```

- **Frontend**: React with Vite
- **Backend**: FastAPI + SQLModel + SQLite
- **Worker**: Background task processor using Ollama