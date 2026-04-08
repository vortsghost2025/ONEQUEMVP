# Fix Ollama - remove custom path and restart
Write-Host "Removing OLLAMA_MODELS setting..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', '', 'Machine')

Write-Host "Killing Ollama processes..." -ForegroundColor Yellow
taskkill /F /IM "ollama app.exe" 2>$null
taskkill /F /IM ollama.exe 2>$null

Write-Host "Starting Ollama..." -ForegroundColor Yellow
Start-Process "ollama app"

Write-Host "Waiting 10 seconds for Ollama to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Pulling llama3..." -ForegroundColor Yellow
ollama pull llama3

Write-Host "Done!" -ForegroundColor Green
