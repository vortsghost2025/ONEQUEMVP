# OneQueue Safety Features - Implementation Summary

## What Was Built

### 1. Pre-Flight Checklist (`app/services/preflight.py`)
**Runs BEFORE any task processing starts**

**Critical Checks (MUST PASS):**
- ✅ Database connection accessible
- ✅ At least one backend available (Ollama OR NVIDIA API)
- ✅ Configuration valid

**Non-Critical Checks (Warning Only):**
- ⚠️ Disk space available
- ⚠️ RAM available

**Behavior:**
```python
# In app/main.py startup
from app.services.preflight import run_preflight_checklist

if not await run_preflight_checklist():
    # Logs errors to logs/preflight_failure_YYYYMMDD_HHMMSS.log
    # OneQueue REFUSES to start
    sys.exit(1)
```

**Example Output:**
```
============================================================
ONEQUEUE PRE-FLIGHT CHECKLIST
============================================================
✓ Database Connection: Database accessible
✗ Backend Availability: No backends available
  Fix: Start Ollama: ollama serve
       OR set NVIDIA_API_KEY in .env
✓ Configuration: Configuration valid
✓ Disk Space: 847.3GB free (12.4% used)
✓ RAM Available: 24.1GB available (48% used)
============================================================
✗ PREFLIGHT FAILED - Critical checks failed:
  - Backend Availability: No backends available
OneQueue will NOT start until critical issues are resolved.
============================================================
```

---

### 2. Backend Health Checker (`app/services/backend_health.py`)
**Prevents running tasks when backends are down**

**Features:**
- Ollama health check (connection + models)
- NVIDIA API health check (key validation + endpoint)
- 30-second cache to avoid spam
- Quick `should_process_tasks()` check for worker

**Worker Integration:**
```python
from app.services.backend_health import get_backend_checker

checker = get_backend_checker()
should_process, reason = await checker.should_process_tasks()

if not should_process:
    logger.warning(f"Skipping tasks: {reason}")
    await asyncio.sleep(poll_interval)
    continue
```

---

### 3. Service Monitoring & Alerting (`app/services/service_monitor.py`)
**Continuous monitoring with automatic notifications**

**Monitors:**
- Ollama backend (every 30s)
- NVIDIA API (every 30s)
- Database (every 30s)

**Alert Channels:**
1. **Agent Notification** (logger)
   - `🚨 SERVICE ALERT: OLLAMA is OFFLINE`
   - `✓ SERVICE RECOVERY: OLLAMA is HEALTHY again`

2. **User Notification** (UI badge)
   - Writes to `data/alerts/current_alerts.json`
   - UI can display alert badges

3. **Alert History**
   - All alerts stored in memory (last 50)
   - Timestamps + metadata

**Smart Alerting:**
- Requires 3 consecutive failures before OFFLINE alert (avoid false positives)
- Requires 1 success before HEALTHY alert
- 5-minute cooldown between same alerts (avoid spam)

**UI Integration:**
```javascript
// Frontend can poll for alerts
fetch('/api/service-alerts')
  .then(res => res.json())
  .then(alerts => {
    // Display badges for offline services
    alerts.forEach(alert => {
      showNotification(`⚠️ ${alert.service}: ${alert.message}`);
    });
  });
```

---

## Startup Sequence

```
1. FastAPI app starts
   ↓
2. Pre-flight checklist runs
   ├─ ✓ Database OK?
   ├─ ✓ Backend available?
   ├─ ✓ Config valid?
   └─ If ANY critical check fails → EXIT
   ↓
3. SQLite WAL mode enabled
   ↓
4. Tables created
   ↓
5. Default Settings inserted
   ↓
6. RUNNING tasks recovered as FAILED
   ↓
7. Background worker starts
   ↓
8. Service monitoring starts (30s interval)
   ↓
9. OneQueue ready to serve requests
```

---

## What's Fixed

**Before:**
- ❌ Worker ran tasks even when Ollama was down
- ❌ No pre-flight checks
- ❌ No service monitoring
- ❌ No alerts when services went offline

**After:**
- ✅ Pre-flight checklist runs at startup
- ✅ Worker checks backend health before processing
- ✅ Service monitoring runs every 30 seconds
- ✅ Automatic alerts when services go down
- ✅ Automatic recovery notifications
- ✅ Alert cooldown prevents spam

---

## Files Created

1. `app/services/preflight.py` - Pre-flight checklist
2. `app/services/backend_health.py` - Backend health checker
3. `app/services/service_monitor.py` - Service monitoring & alerting

## Files Modified

1. `app/main.py` - Integrated pre-flight + service monitoring into startup

---

## Testing

### Test Pre-Flight Failure
```bash
# Stop Ollama
pkill ollama

# Start OneQueue
python -m uvicorn app.main:app --host 127.0.0.1 --port 8081

# Expected: OneQueue refuses to start
# Output: "✗ PREFLIGHT FAILED - Backend Availability: No backends available"
```

### Test Service Monitoring
```bash
# Start OneQueue (with both backends healthy)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8081

# Wait 30s, then kill Ollama
pkill ollama

# Expected: Alert logged
# Output: "🚨 SERVICE ALERT: OLLAMA is OFFLINE"

# Restart Ollama
ollama serve &

# Expected: Recovery logged
# Output: "✓ SERVICE RECOVERY: OLLAMA is HEALTHY again"
```

---

## Next Steps

1. **Add UI badge component** - Display alerts in frontend
2. **Add webhook integration** - Send alerts to Slack/Discord
3. **Add email notifications** - Critical alerts via email
4. **Add Prometheus metrics** - Export service health metrics
5. **Add Grafana dashboard** - Visualize service uptime

---

## Environment Variables

Add to `.env`:
```bash
# Alert settings (optional)
ALERT_COOLDOWN_MINUTES=5
SERVICE_CHECK_INTERVAL_SECONDS=30
OFFLINE_THRESHOLD=3
RECOVERY_THRESHOLD=1
```

---

## Logs Location

- Pre-flight failures: `logs/preflight_failure_YYYYMMDD_HHMMSS.log`
- Service alerts: `data/alerts/current_alerts.json`
- Runtime logs: stdout (captured by uvicorn)
