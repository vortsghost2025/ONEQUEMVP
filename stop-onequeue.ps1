# OneQueue Stop Script

Write-Host "=== Stopping OneQueue Services ===" -ForegroundColor Cyan

# Stop Ollama
$ollama = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "[1/3] Stopping Ollama..." -ForegroundColor Yellow
    Stop-Process -Name "ollama" -Force
    Write-Host "   Ollama stopped" -ForegroundColor Green
} else {
    Write-Host "[1/3] Ollama not running" -ForegroundColor Gray
}

# Stop Backend (uvicorn on port 8080)
$backend = netstat -ano | findstr ":8080.*LISTENING"
if ($backend) {
    Write-Host "[2/3] Stopping Backend..." -ForegroundColor Yellow
    $backend -match "(\d+)$" | Out-Null
    $pid = $matches[1]
    Stop-Process -Id $pid -Force
    Write-Host "   Backend stopped" -ForegroundColor Green
} else {
    Write-Host "[2/3] Backend not running" -ForegroundColor Gray
}

# Stop Frontend (npm on port 5173)
$frontend = netstat -ano | findstr ":5173.*LISTENING"
if ($frontend) {
    Write-Host "[3/3] Stopping Frontend..." -ForegroundColor Yellow
    $frontend -match "(\d+)$" | Out-Null
    $pid = $matches[1]
    Stop-Process -Id $pid -Force
    Write-Host "   Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "[3/3] Frontend not running" -ForegroundColor Gray
}

# Update status
$status = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    ollama = $false
    backend = $false
    frontend = $false
}
$status | ConvertTo-Json | Out-File -FilePath "status.json" -Encoding UTF8

Write-Host "`n=== All Services Stopped ===" -ForegroundColor Cyan
