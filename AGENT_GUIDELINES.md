# 🤖 Agent Guidelines - MANDATORY FOR ALL AGENTS

## ⚠️ CRITICAL: Read Before ANY Action

**These guidelines are ENFORCED. Every agent MUST follow them.**

---

## The 4 Golden Rules

### Rule #1: Document Everything
- **EVERY** action must be logged
- Include: timestamp, Agent ID, action, reason, files changed, test results
- No exceptions - even "small" changes
- Format: See `AGENT_ACTIVITY_LOG.md`

### Rule #2: Local Storage Only
- Logs: `S:\TAKE10\logs\`
- Activity log: `S:\TAKE10\AGENT_ACTIVITY_LOG.md`
- **NEVER** store logs on VPS
- VPS is for deployment ONLY

### Rule #3: Agent ID Format
```${AgentName}_{YYYYMMDD}_{SequenceNumber}```

Examples:
- `GLM_20260409_001`
- `AIdea_20260409_002`
- `System_20260409_003`

### Rule #4: Test Everything
- Test before committing
- Log test results (pass/fail + details)
- Provide rollback plan
- Never push untested code to VPS

---

## Before You Start

### Step 1: Check In
Run this BEFORE any action:
```powershell
cd S:\TAKE10
.\scripts\agent-checkin.ps1 -AgentID "YourAgent_YYYYMMDD_SEQ" -Action "What you're doing"
```

### Step 2: Read Activity Log
**MANDATORY:** Read `AGENT_ACTIVITY_LOG.md` to see:
- What's been done
- What's pending
- Known issues
- Current status

### Step 3: Declare Intent
Add entry to activity log with:
- What you're doing
- Why
- Expected outcome
- Files you'll change

---

## During Work

### Logging Changes
For EACH change:
1. Update `AGENT_ACTIVITY_LOG.md`
2. Update `logs\agent_log.json`
3. Include timestamp and Agent ID
4. Document test results

### Testing Requirements
- ✅ Unit tests pass
- ✅ Integration tests pass
- ✅ No regressions
- ✅ Rollback plan ready
- ✅ Logs updated

---

## After Completion

### Update Logs
```markdown
### Entry #{NUMBER}
- **Timestamp:** 2026-04-09 HH:MM:SS UTC
- **Agent ID:** {YourAgentID}
- **Action:** {What was done}
- **Reason:** {Why}
- **Files Changed:** {List all files}
- **Test Results:** {Pass/Fail + details}
- **Status:** {Complete/Pending/Failed}
```

### Update JSON Log
Add entry to `logs\agent_log.json`:
- Increment entry number
- Add your entry
- Update `last_updated`
- Update `total_entries`

---

## Project Status

### Current State
- ✅ OneQueue deployed on VPS (187.77.3.56:8081)
- ✅ Ollama running (187.77.3.56:11434)
- ✅ Pre-flight checklist active
- ✅ Service monitoring enabled (30s)
- ⏳ Startup Notifier (pending deployment)
- ⏳ AIdeaChat (pending GLM tests)

### Known Issues
1. Ollama downtime - detected by pre-flight, alerts via status endpoint
2. Notification system - being deployed (Entry #002)
3. Agent documentation - FIXED by this system

### Pending Actions
- [ ] Deploy startup notifier
- [ ] Test AIdeaChat after GLM
- [ ] Add Slack/Discord webhooks
- [ ] Auto-backup logs daily

---

## File Structure

```
S:\TAKE10/
├── AGENT_ACTIVITY_LOG.md       # Main activity log (UPDATE THIS)
├── AGENT_GUIDELINES.md         # This file (READ THIS)
├── logs/
│   └── agent_log.json          # JSON log (UPDATE THIS)
├── scripts/
│   ├── agent-checkin.ps1       # Check-in script (RUN THIS)
│   └── agent-log-entry.ps1     # Add log entry (RUN THIS)
├── app/
│   ├── main.py                 # Main application
│   ├── api/                    # API endpoints
│   └── services/               # Services
└── frontend/
    └── src/                    # React components
```

---

## Emergency Procedures

### If VPS Goes Down
1. Check status: `ssh root@187.77.3.56 "docker ps"`
2. Check logs: `ssh root@187.77.3.56 "docker logs onequeue"`
3. Restart if needed: `ssh root@187.77.3.56 "cd /opt/onequeue && docker compose restart"`
4. **LOG THE INCIDENT**

### If Tests Fail
1. Rollback immediately
2. Document failure in logs
3. Fix and retest
4. **LOG THE FAILURE**

### If Agent Violates Guidelines
1. Stop the agent
2. Review what was done
3. Fix any unlogged changes
4. **LOG THE VIOLATION**

---

## Contact

- **Project:** OneQueue
- **VPS:** 187.77.3.56
- **Local Path:** S:\TAKE10
- **Log Path:** S:\TAKE10\logs\agent_log.json

---

**Last Updated:** 2026-04-09 18:33:00 UTC  
**Version:** 1.0  
**Enforced By:** All agents
