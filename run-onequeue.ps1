# OneQueue Simple Runner
# No Docker required!

Write-Host "=== OneQueue Simple Runner ===" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found! Install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$depCheck = python -c "import sqlmodel" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " Dependencies OK" -ForegroundColor Green
} else {
    Write-Host " Installing dependencies..." -ForegroundColor Gray
    pip install -r requirements.txt
}

# Kill any existing process on port 8081
Write-Host "Cleaning up port 8081..." -ForegroundColor Yellow
$existingProcess = netstat -ano | findstr :8081
if ($existingProcess) {
    $pid = ($existingProcess -split '\s+')[-1]
    if ($pid -match '^\d+$') {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host " Killed process $pid" -ForegroundColor Gray
    }
}

# Run OneQueue
Write-Host ""
Write-Host "Starting OneQueue..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Auto-restart on crash
$restartCount = 0
$maxRestarts = 3

while ($restartCount -lt $maxRestarts) {
    try {
        python -m uvicorn app.main:app --host 127.0.0.1 --port 8081 --reload
        # If we get here, app exited cleanly
        Write-Host "OneQueue stopped" -ForegroundColor Yellow
        break
    } catch {
        $restartCount++
        Write-Host "Crashed! Restarting ($restartCount/$maxRestarts)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if ($restartCount -ge $maxRestarts) {
    Write-Host "Too many restarts. Please check logs." -ForegroundColor Red
}
