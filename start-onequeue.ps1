# OneQueue Launch Script
# YOU run this, I orchestrate what it does

Write-Host "=== OneQueue Launch Script ===" -ForegroundColor Cyan

# Check if Ollama is running
$ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "[1/3] Starting Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "   Ollama started" -ForegroundColor Green
} else {
    Write-Host "[1/3] Ollama already running" -ForegroundColor Green
}

# Check if backend is running on port 3000
$backendRunning = netstat -ano | findstr ":3000.*LISTENING"
if (-not $backendRunning) {
    Write-Host "[2/3] Starting Backend (uvicorn)..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "3000" -WindowStyle Minimized -WorkingDirectory $PSScriptRoot
    Start-Sleep -Seconds 5
    Write-Host " Backend started on http://127.0.0.1:3000" -ForegroundColor Green
} else {
    Write-Host "[2/3] Backend already running" -ForegroundColor Green
}

# Check if frontend is running on port 5173
$frontendRunning = netstat -ano | findstr ":5173.*LISTENING"
if (-not $frontendRunning) {
    Write-Host "[3/3] Starting Frontend (npm dev)..." -ForegroundColor Yellow
    Set-Location frontend
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WindowStyle Minimized
    Set-Location ..
    Start-Sleep -Seconds 5
    Write-Host "   Frontend started on http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "[3/3] Frontend already running" -ForegroundColor Green
}

# Write status to JSON for agent to read
$status = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    ollama = (Get-Process -Name "ollama" -ErrorAction SilentlyContinue) -ne $null
    backend = (netstat -ano | findstr ":3000.*LISTENING") -ne $null
    frontend = (netstat -ano | findstr ":5173.*LISTENING") -ne $null
}

$status | ConvertTo-Json | Out-File -FilePath "status.json" -Encoding UTF8

Write-Host "`n=== All Services Started ===" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend: http://127.0.0.1:3000" -ForegroundColor White
Write-Host "API Docs: http://127.0.0.1:3000/docs" -ForegroundColor White
Write-Host "`nPress any key to open browser..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:5173"
