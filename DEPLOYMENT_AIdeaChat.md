# AIdeaChat Deployment Guide

## Status
- ✅ Local Development: Complete
- ⏳ VPS Deployment: Pending (waiting for GLM tests to finish)

## Files to Deploy to VPS

### 1. Backend Files

#### `/opt/onequeue/app/api/ai_idea.py`
```python
"""
AI Idea Planner API Endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.ai_idea_planner import get_planner

router = APIRouter()

class IdeaRequest(BaseModel):
    message: str

class IdeaResponse(BaseModel):
    response: str
    taskPlan: Dict[str, Any] | None = None

@router.post("/", response_model=IdeaResponse)
async def parse_idea(request: IdeaRequest):
    try:
        planner = get_planner()
        result = await planner.parse_idea(request.message)
        return IdeaResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### `/opt/onequeue/app/ai_idea_planner.py`
(Already created locally at `S:\TAKE10\app\ai_idea_planner.py`)

#### Update `/opt/onequeue/app/main.py`
Add to imports (around line 19-26):
```python
from app.api import (
    tasks,
    settings as settings_router,
    queue as queue_router,
    nvidia as nvidia_router,
    router_api,
    ai_idea,  # ← ADD THIS
)
```

Add to routers (around line 122):
```python
app.include_router(ai_idea.router, prefix="/ai-idea", tags=["ai-idea"])
```

### 2. Frontend Files

#### `/opt/onequeue/frontend/src/components/AIdeaChat.jsx`
(Already created locally)

#### `/opt/onequeue/frontend/src/components/AIdeaChat.css`
(Already created locally)

#### Update `/opt/onequeue/frontend/src/App.jsx`
- Import AIdeaChat component
- Add "AI Ideas" tab
- Add tab content section

## Deployment Steps (AFTER GLM Tests Complete)

### Step 1: Backup Current State
```bash
ssh root@187.77.3.56 "cd /opt/onequeue && tar -czf backup-before-aiidea-$(date +%Y%m%d).tar.gz ./"
```

### Step 2: Upload Backend Files
```bash
# Upload AI planner
scp S:\TAKE10\app\ai_idea_planner.py root@187.77.3.56:/opt/onequeue/app/

# Upload API router
scp S:\TAKE10\app\api\ai_idea.py root@187.77.3.56:/opt/onequeue/app/api/
```

### Step 3: Update main.py
Edit `/opt/onequeue/app/main.py` to add the router import and registration.

### Step 4: Upload Frontend Files
```bash
scp S:\TAKE10\frontend\src\components\AIdeaChat.jsx root@187.77.3.56:/opt/onequeue/frontend/src/components/
scp S:\TAKE10\frontend\src\components\AIdeaChat.css root@187.77.3.56:/opt/onequeue/frontend/src/components/
```

### Step 5: Update App.jsx
Edit `/opt/onequeue/frontend/src/App.jsx` to include AIdeaChat.

### Step 6: Rebuild Frontend
```bash
ssh root@187.77.3.56 "cd /opt/onequeue/frontend && npm run build"
```

### Step 7: Restart Services
```bash
ssh root@187.77.3.56 "cd /opt/onequeue && docker compose restart"
```

## Testing After Deployment

1. Open http://187.77.3.56:8081
2. Click "AI Ideas" tab (💡 icon)
3. Test with: "Create 3 tasks to analyze customer feedback"
4. Verify AI breaks it down into structured tasks
5. Approve and verify tasks are created

## Rollback Plan
If issues occur:
```bash
ssh root@187.77.3.56 "cd /opt/onequeue && docker compose down"
ssh root@187.77.3.56 "cd /opt/onequeue && tar -xzf backup-before-aiidea-*.tar.gz"
ssh root@187.77.3.56 "cd /opt/onequeue && docker compose up -d"
```

## Current Status
- ⏳ Waiting for GLM end-to-end tests to complete
- 📝 Deployment guide ready
- 📦 Files prepared locally
- 🚀 Ready to deploy after tests
