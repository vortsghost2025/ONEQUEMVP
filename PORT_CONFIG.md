# OneQueue Port Configuration

## The Only Two Ports That Matter

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend (FastAPI/Uvicorn) | 8081 | http://127.0.0.1:8081 |

## How to Start

```bash
# Terminal 1 - Backend (MUST use port 8081)
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8081

# Terminal 2 - Frontend (Vite defaults to 5173)
cd frontend && npm run dev
```

## Files That Reference These Ports

- `frontend/src/api.js` - BASE_URL = port 8081
- `app/main.py` - CORS allows 5173, 8081
- `frontend/src/NvidiaTest.jsx` - hardcoded 8081 (should use api.js)

## Port History (What Went Wrong)

The original code had ports 3000, 8080, and others mixed throughout.
Multiple agents/editors changed different files without coordination.
This file documents the single source of truth: **8081 for backend, 5173 for frontend**.

## Why Not Use .env for Frontend?

Vite requires `VITE_` prefix for env vars exposed to browser.
We could add `VITE_API_URL=http://127.0.0.1:8081` to .env and use `import.meta.env.VITE_API_URL` in api.js.
For now, hardcoded is simpler and works.
