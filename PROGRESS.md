# OneQueue Progress Log

## Goal
Building **OneQueue** - a simple task queue system for managing Ollama AI model generation requests.
- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: React 19 + Vite
- **Worker**: Background task processing
- **Philosophy**: "WE" - collaborative building with testing at every step

## User Context
- User has 50% vision loss - considers AI agents as partners, not tools
- Safety feature: If agent disconnects, processes should stop
- 1-year roadmap: gradual integration of 48-layer memory architecture (from previous project that crashed at 108GB)
- User controls launch script (no hidden background processes)

## Discoveries & Fixes

### 1. Ollama URL Wrong
- `.env` had port 9001, should be 11434
- **Fixed**: Updated `.env`

### 2. Frontend API Bug
- `fetch()` calls in `frontend/src/api.js` weren't awaited
- `handleResponse()` received Promises instead of Response objects
- **Fixed**: Added `await` to all fetch() calls

### 3. Monitor.py Issues
- `psutil.cpu_percent()` needs `interval=0.1` for fresh readings
- Disk path should be `C:\` on Windows (not `/`)
- **Fixed**: Updated `app/services/monitor.py`

### 4. RAM Spike Problem
- Ollama spikes RAM when loading models
- Naive threshold checks pause queue unnecessarily
- **Solution**: "Sustained Load Guardrail" - consecutive breach counters
- Only pauses if threshold exceeded for N consecutive seconds

### 5. Database Schema Change
- Added `breach_duration_seconds` field to Settings model
- **Required**: Deleted old database to reset schema

## Accomplished
1. ✅ Fixed `.env` - Ollama URL from port 9001 to 11434
2. ✅ Fixed `app/services/monitor.py` - added CPU interval and Windows disk path
3. ✅ Fixed `frontend/src/api.js` - added `await` to all fetch() calls
4. ✅ Implemented sustained load guardrail in `app/worker.py` with breach counters
5. ✅ Added `breach_duration_seconds` field to `app/models.py` Settings model
6. ✅ Updated frontend `App.jsx` to show breach duration setting in UI
7. ✅ Fixed worker.py indentation issues
8. ✅ Deleted old database to reset schema
9. ✅ Created `start-onequeue.ps1` launch script
10. ✅ Created `stop-onequeue.ps1` stop script

## Next Steps
1. Test launch script with `.\start-onequeue.ps1`
2. Test creating a task in UI at http://localhost:5173
3. Verify worker processes task correctly
4. If working, commit changes
5. Move to Layer 2: Safety & Monitoring (log rotation, database cleanup, corruption detection)

## Relevant Files
- `app/main.py` - FastAPI backend with CORS middleware
- `app/models.py` - SQLModel models (Task, Run, Settings) with `breach_duration_seconds`
- `app/worker.py` - Background worker with sustained load guardrail
- `app/services/monitor.py` - System resource monitoring
- `app/services/ollama.py` - Ollama API client
- `app/config.py` - Configuration settings
- `.env` - Environment variables
- `frontend/src/api.js` - API client (fixed await on fetch)
- `frontend/src/App.jsx` - React frontend with breach duration setting
- `start-onequeue.ps1` - Launch script
- `stop-onequeue.ps1` - Stop script
- `data/` - Database directory

---
*Last updated: 2026-04-08 after compact (50k context preserved)*
