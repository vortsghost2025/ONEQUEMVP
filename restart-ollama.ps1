# Restart Ollama fresh
Write-Host "Killing Ollama..." -ForegroundColor Yellow
taskkill /F /IM "ollama app.exe" 2>$null
taskkill /F /IM ollama.exe 2>$null

Write-Host "Waiting 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Starting Ollama..." -ForegroundColor Yellow
Start-Process "ollama app"

Write-Host "Waiting 10 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Checking Ollama status..." -ForegroundColor Yellow
curl http://localhost:11434/api/tags

Write-Host "`nPulling llama3..." -ForegroundColor Yellow
ollama pull llama3
