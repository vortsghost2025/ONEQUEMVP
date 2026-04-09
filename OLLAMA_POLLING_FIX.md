# Ollama Polling Issue - Summary & Fix

## Problem
Ollama API endpoint `localhost:11434/api/tags` being polled every 31 seconds.

## Root Cause
**Ollama Snowman app** (GUI application) polls its own local API to refresh the model list display. This is **normal UI behavior**, not malicious.

## Current Processes
- `ollama app.exe` (PID 36248) - **Snowman GUI** (the source of polling)
- `ollama.exe` (PID 14212) - Ollama server
- `ollama.exe` (PID 29336) - Another Ollama instance

## Solution
The app is protected and cannot be killed without admin rights.

### Option 1: Kill as Admin (Recommended)
```powershell
# Right-click PowerShell -> Run as Administrator
Stop-Process -Id 36248 -Force
```

Or run: `S:\TAKE10\kill-ollama-app.ps1` as Admin

### Option 2: Disable Auto-Start
1. Open Task Manager → Startup apps
2. Disable "Ollama" if present
3. Only open Ollama app when needed

### Option 3: Uninstall Ollama App
1. Settings → Apps → Installed apps
2. Find "Ollama"
3. Uninstall (keeps `ollama.exe` CLI tool)

### Option 4: Just Close It
When not using the GUI, close the Ollama Snowman app window. The `ollama serve` will continue working.

## OneQueue Frontend Polling
Also check: `S:\TAKE10\frontend\src\App.jsx` has `POLL_INTERVAL = 3000` (3 seconds). This is for task queue updates and is separate from the Ollama app polling.

## Summary
- **Not malicious** - it's the Ollama Snowman app's normal behavior
- **Low resource usage** - ~17MB memory, localhost only
- **Easy fix** - close the app or run kill script as admin
