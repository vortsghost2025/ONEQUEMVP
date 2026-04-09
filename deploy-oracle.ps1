# OneQueue - Deploy to Oracle Cloud
# This uploads and deploys your OneQueue to Oracle Cloud VM

$oracleHost = "your-oracle-vm-ip"
$oracleUser = "opc"
$oraclePath = "/home/opc/onequeue"

Write-Host "=== OneQueue Oracle Cloud Deploy ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build Docker image
Write-Host "[1/4] Building Docker image..." -ForegroundColor Yellow
docker-compose build

# Step 2: Save image
Write-Host "[2/4] Saving Docker image..." -ForegroundColor Yellow
docker save onequeue-onequeue:latest | gzip > onequeue-image.tar.gz

# Step 3: Upload to Oracle
Write-Host "[3/4] Uploading to Oracle Cloud..." -ForegroundColor Yellow
scp onequeue-image.tar.gz ${oracleUser}@${oracleHost}:~/

# Step 4: Deploy on Oracle
Write-Host "[4/4] Deploying on Oracle Cloud..." -ForegroundColor Yellow
ssh ${oracleUser}@${oracleHost} @"
  docker load < onequeue-image.tar.gz
  docker-compose up -d
"@

Write-Host ""
Write-Host "Deploy complete!" -ForegroundColor Green
Write-Host "Your OneQueue is running at: http://${oracleHost}:8081" -ForegroundColor Cyan
