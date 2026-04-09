# Start Docker Desktop and wait for it
Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

Write-Host "Waiting for Docker to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "Docker is ready!" -ForegroundColor Green
Write-Host "Now you can run: docker-compose up" -ForegroundColor Cyan
