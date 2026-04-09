# Docker Setup - Step 3 of 3
# This creates your OneQueue Docker files

Write-Host "Creating Docker files for OneQueue..." -ForegroundColor Yellow

# Create Dockerfile
$dockerfileContent = @"
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8081
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
"@

Set-Content -Path "S:\TAKE10\Dockerfile" -Value $dockerfileContent
Write-Host "Created Dockerfile" -ForegroundColor Green

# Create docker-compose.yml
$composeContent = @'
version: '3.8'
services:
  onequeue:
    build: .
    ports:
      - "8081:8081"
    volumes:
      - .:/app
      - onequeue-data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/onequeue.db
    restart: unless-stopped
volumes:
  onequeue-data:
'@

Set-Content -Path "S:\TAKE10\docker-compose.yml" -Value $composeContent
Write-Host "Created docker-compose.yml" -ForegroundColor Green

Write-Host "" -ForegroundColor White
Write-Host "STEP 3 DONE!" -ForegroundColor Green
Write-Host "Your OneQueue Docker setup is ready!" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "To run OneQueue with Docker:" -ForegroundColor Yellow
Write-Host "  docker-compose up" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "To deploy to Oracle Cloud next:" -ForegroundColor Yellow
Write-Host "  Run: S:\TAKE10\deploy-oracle.ps1" -ForegroundColor White
