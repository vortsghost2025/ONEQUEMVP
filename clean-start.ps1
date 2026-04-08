# OneQueue Clean Start - Uses PowerShell 7
# Run this with: pwsh -File .\clean-start.ps1

Write-Host "=== OneQueue Clean Start ===" -ForegroundColor Cyan
Write-Host "Using PowerShell $($PSVersionTable.PSVersion)" -ForegroundColor Gray

# Kill all processes
Write-Host "`n[1/4] Killing existing processes..." -ForegroundColor Yellow
Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "  Done" -ForegroundColor Green

# Start Ollama
Write-Host "`n[2/4] Starting Ollama..." -ForegroundColor Yellow
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
Start-Sleep -Seconds 3
Write-Host "  Ollama running" -ForegroundColor Green

# Start Backend
Write-Host "`n[3/4] Starting Backend (port 3000)..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "3000" -WindowStyle Minimized
Start-Sleep -Seconds 3
Write-Host "  Backend at http://127.0.0.1:3000" -ForegroundColor Green

# Start Frontend
Write-Host "`n[4/4] Starting Frontend..." -ForegroundColor Yellow
Push-Location frontend
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WindowStyle Minimized
Pop-Location
Start-Sleep -Seconds 3
Write-Host "  Frontend at http://localhost:5173" -ForegroundColor Green

Write-Host "`n=== All Services Started ===" -ForegroundColor Cyan
Write-Host "Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "Backend:   http://127.0.0.1:3000/docs" -ForegroundColor White
Write-Host "Ollama:    http://localhost:11434" -ForegroundColor White
Write-Host "`nPull a model first: ollama pull llama3" -ForegroundColor Gray
