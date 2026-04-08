# Deployment Guide

## Quick Start

Deploy the entire OneQueue MVP stack with a single command:

```bash
docker-compose up -d
```

This starts all services:
- **API** (FastAPI): http://localhost:8000
- **Frontend** (React/Vite): http://localhost:5173  
- **Ollama** (LLM runtime): http://localhost:11434

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI backend with SQLite |
| Frontend | 5173 | React Vite dev server |
| Ollama | 11434 | LLM runtime (CPU) |

## Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `http://localhost:8000/health` | `{"status": "healthy", "service": "onequeue-api"}` |
| Frontend | `http://localhost:5173` | HTTP 200 (curl -f) |
| Ollama | `http://localhost:11434/api/tags` | JSON list of models |

## Configuration

Environment variables can be configured in `docker-compose.yml` or via `.env`:

```bash
OLLAMA_BASE_URL=http://ollama:11434
DATABASE_URL=sqlite:///./data/onequeue.db
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=1.0
```

## Data Persistence

- **SQLite DB**: `./data/onequeue.db` (mapped from host)
- **Ollama models**: Docker volume `ollama-data`

## Development Mode

For live development with hot reload:

```bash
# Backend (from project root)
uvicorn app.main:app --reload

# Frontend (from frontend/)
npm run dev
```

## Production Build

```bash
# Build production images
docker-compose build

# Run production stack
docker-compose -f docker-compose.yml up -d
```

## Stopping Services

```bash
docker-compose down
```

To also remove volumes (data loss):
```bash
docker-compose down -v
```
