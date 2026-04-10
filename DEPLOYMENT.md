# Deployment Guide

## Quick Start

Deploy the entire OneQueue MVP stack with a single command:

```bash
docker-compose up -d
```

This starts all services:
- **API** (FastAPI): http://localhost:8000
- **Frontend** (React/Vite): http://localhost:5173
- **Worker**: Background task processor
- **Ollama** (LLM runtime): http://localhost:11434

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended for Ollama)

## Services

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| API | 8000 | FastAPI backend with SQLite | `/health` |
| Frontend | 5173 | React Vite dev server | `/` |
| Worker | - | Background task processor | Via API |
| Ollama | 11434 | LLM runtime (CPU/GPU) | `/api/tags` |

## Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `http://localhost:8000/health` | `{"status": "healthy", "service": "onequeue-api"}` |
| Frontend | `http://localhost:5173` | HTTP 200 |
| Ollama | `http://localhost:11434/api/tags` | JSON list of models |

### Docker Health Checks

All services include built-in health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

View container health status:
```bash
docker-compose ps
docker inspect onequeue-api --format='{{.State.Health.Status}}'
```

## Configuration

Environment variables can be configured in `docker-compose.yml` or via `.env`:

```bash
# .env file
NVIDIA_API_KEY=your-key-here
OLLAMA_BASE_URL=http://ollama:11434
DATABASE_URL=sqlite:////app/data/onequeue.db
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=1.0
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | - | NVIDIA API key for cloud models |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama server URL |
| `DATABASE_URL` | `sqlite:////app/data/onequeue.db` | SQLite database path |
| `POLLING_INTERVAL_SECONDS` | `1` | Task polling interval |

## Data Persistence

- **SQLite DB**: Docker volume `onequeue-data`
- **Ollama models**: Docker volume `ollama-data`

## Development Mode

For live development with hot reload:

```bash
# Backend (from project root)
uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/)
npm run dev
```

## Production Build

```bash
# Build production images
docker-compose build

# Run production stack
docker-compose up -d
```

## Troubleshooting

### Check Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f worker
docker-compose logs -f ollama
```

### Verify Health Checks

```bash
# API health
curl http://localhost:8000/health

# Ollama models
curl http://localhost:11434/api/tags
```

### Common Issues

1. **Ollama not ready**: Increase `start_period` to 120s for first-time model download
2. **Database locked**: Ensure only one worker container is running
3. **Port conflicts**: Check ports 8000, 5173, 11434 are available

## Stopping Services

```bash
docker-compose down
```

To also remove volumes (data loss):
```bash
docker-compose down -v
```

## Architecture

```
┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│     API     │
│  (5173)     │     │   (8000)    │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Worker    │
                    │ (background)│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  SQLite   │ │  Ollama  │ │ NVIDIA   │
        │  (data)   │ │ (11434) │ │  (cloud) │
        └──────────┘ └──────────┘ └──────────┘
```