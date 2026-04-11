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
| API | 8000 | FastAPI backend with embedded worker + SQLite |
| Frontend | 5173 | React Vite dev server |
| Ollama | 11434 | Local LLM runtime (CPU) |

## Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `GET /health` | `{"status": "healthy", "service": "onequeue-api"}` |
| Queue | `GET /queue/health` | Returns service availability status |
| Frontend | `http://localhost:5173` | HTTP 200 (curl -f) |
| Ollama | `GET http://localhost:11434/api/tags` | JSON list of models |

### Checking Health Status

```bash
# Check API health
curl http://localhost:8000/health
# Response: {"status": "healthy", "service": "onequeue-api"}

# Check queue health (includes Ollama/NVIDIA status)
curl http://localhost:8000/queue/health

# Check Ollama is running
curl http://localhost:11434/api/tags
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NVIDIA_API_KEY` | No | - | API key for NVIDIA NIM cloud models |
| `OLLAMA_BASE_URL` | No | http://ollama:11434 | Ollama API endpoint |
| `DATABASE_URL` | No | sqlite:///./data/onequeue.db | SQLite database path |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `POLLING_INTERVAL_SECONDS` | No | 1.0 | Worker polling interval |

### Using NVIDIA Cloud Models

To use NVIDIA NIM cloud models (e.g., `meta/llama-4-maverick-17b-128e-instruct`), set your API key:

```bash
# Set the environment variable before starting
export NVIDIA_API_KEY=your-nvidia-api-key
docker-compose up -d
```

### Using a .env File

Create a `.env` file in the project root:

```bash
NVIDIA_API_KEY=your-nvidia-api-key
OLLAMA_BASE_URL=http://ollama:11434
LOG_LEVEL=INFO
```

## Data Persistence

- **SQLite DB**: `./data/onequeue.db` (mapped from host volume)
- **Ollama models**: Docker volume `ollama-data`

## Management Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f ollama

# Restart a specific service
docker-compose restart api

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: data loss)
docker-compose down -v

# Rebuild and start
docker-compose up -d --build
```

## Development Mode

For live development with hot reload:

```bash
# Backend (from project root)
uvicorn app.main:app --reload

# Frontend (from frontend/)
cd frontend && npm run dev
```

## Production Build

```bash
# Build production images
docker-compose build

# Run production stack
docker-compose up -d
```

## Troubleshooting

### API Health Check Fails

```bash
# Check if API container is running
docker-compose ps

# View API logs
docker-compose logs api

# Check container health status
docker inspect onequeue-api-1 | jq '.State.Health'
```

### Ollama Not Ready

```bash
# View Ollama logs (first start can take time for model download)
docker-compose logs ollama

# Wait for model download - check logs for progress
# Initial start: 60s start_period + model download time
```

### Database Issues

```bash
# Verify data volume exists
docker volume ls | grep onequeue

# Access database directly
docker-compose exec api sqlite3 /app/data/onequeue.db ".tables"
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI    │────▶│   SQLite    │
│  (React)    │     │  + Worker   │     │  (volume)   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Ollama    │
                    │  (LLMs)     │
                    └─────────────┘
```

- **Frontend**: React with Vite web interface
- **API**: FastAPI backend with embedded background worker
- **Ollama**: Local LLM runtime
- **SQLite**: Persistent task storage
