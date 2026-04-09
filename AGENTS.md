# ONEQUEUE PROJECT - AGENT INSTRUCTIONS

## ⚠️ MANDATORY: READ BEFORE ANY WORK ⚠️

**ALL AGENTS MUST READ AND FOLLOW THESE RULES:**

1. **READ** `.kilo/AGENT_ACTIVITY_LOG.md` before starting ANY work
2. **LOG** every single action in the activity log
3. **FOLLOW** the logging format exactly (see `.kilo/command/start.md`)

---

## PROJECT OVERVIEW

OneQueue is an intelligent AI model routing system with:
- FastAPI backend (Python)
- SQLite database with SQLModel
- NVIDIA API integration
- Ollama local model support
- Docker deployment
- Pre-flight safety checks
- Service monitoring

---

## CRITICAL FILES

### Agent Activity Log (MANDATORY)
- `.kilo/AGENT_ACTIVITY_LOG.md` - **READ THIS FIRST**
- `.kilo/command/start.md` - Logging rules

### Configuration
- `kilo.json` - Project config
- `.kilo/` - Agent commands and configs

### Application
- `app/main.py` - FastAPI entry point
- `app/services/preflight.py` - Pre-flight checklist
- `app/services/service_monitor.py` - Service monitoring
- `app/worker.py` - Background worker
- `app/models/` - Database models

### Deployment
- `docker-compose.yml` - Docker configuration
- VPS: `187.77.3.56` (root SSH access)

---

## LOGGING REQUIREMENTS

**Every action must be logged with:**
- Timestamp (ISO 8601)
- Agent ID (your model name)
- Action type
- Description
- Files affected
- Result

**Example:**
```markdown
### 2026-04-09T09:22:40-04:00 | Agent: kilo (z-ai/glm5)
**Action**: MODIFY
**Description**: Added service monitor to startup
**Files**: 
- app/main.py
**Result**: success
```

---

## CURRENT STATUS

**Last Updated**: 2026-04-09T09:22:40-04:00

### Active Work
- Service monitor integration pending
- LSP errors in router files (non-blocking)
- VPS deployment verified working

### VPS Status
- OneQueue running on 187.77.3.56
- Pre-flight checklist active
- End-to-end tests passing

### Known Issues
- Import errors in `app/api/router_api.py` (smart_router, benchmark_system)
- Type errors in `app/services/router_function.py`
- Worker ordering syntax issues

---

## AGENT IDS

| Agent | Model | Identifier |
|-------|-------|------------|
| Kilo | GLM5 | z-ai/glm5 |
| OpenCode Qwen | Qwen 3.5 | (pending) |

---

## ENFORCEMENT

**Agents that fail to log actions will be flagged.**

The activity log is the source of truth for:
- What changes were made
- When they were made
- Who made them
- What the result was

**No logging = No action**

---

## QUICK START

1. Read `.kilo/AGENT_ACTIVITY_LOG.md`
2. Check current status
3. Log your presence
4. Do your work
5. Log your actions
6. Update result

---

**REMEMBER**: If it's not logged, it didn't happen.
