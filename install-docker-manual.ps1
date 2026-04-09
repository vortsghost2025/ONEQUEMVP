# Manual Docker Desktop Install with Progress
Write-Host "=== Docker Desktop Installation ===" -ForegroundColor Cyan
Write-Host ""

# Check if already installed
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Write-Host "Docker Desktop is already installed!" -ForegroundColor Green
    Write-Host "Location: $dockerPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process $dockerPath
    Write-Host "Please wait for Docker Desktop to fully start (whale icon in tray)" -ForegroundColor Cyan
    Write-Host "Then run: docker-compose up" -ForegroundColor White
    exit 0
}

# Download Docker Desktop
Write-Host "Step 1: Downloading Docker Desktop..." -ForegroundColor Yellow
$downloadUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

try {
    Write-Host "  Downloading from: $downloadUrl" -ForegroundColor Gray
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    $ProgressPreference = 'Continue'
    Write-Host "  Download complete: $($installerPath)" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Download failed - $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual download option:" -ForegroundColor Yellow
    Write-Host "1. Open browser to: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -ForegroundColor Gray
    Write-Host "2. Save to: $installerPath" -ForegroundColor Gray
    Write-Host "3. Run the installer" -ForegroundColor Gray
    exit 1
}

# Run installer
Write-Host ""
Write-Host "Step 2: Running installer..." -ForegroundColor Yellow
Write-Host "Docker Desktop will open and ask for permissions" -ForegroundColor Gray
Write-Host "Accept the defaults and let it install WSL2 backend" -ForegroundColor Gray
Write-Host ""

Start-Process $installerPath -ArgumentList "install", "--quiet" -Wait

# Verify installation
Write-Host ""
Write-Host "Step 3: Verifying installation..." -ForegroundColor Yellow
if (Test-Path $dockerPath) {
    Write-Host "SUCCESS! Docker Desktop installed at: $dockerPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Open Docker Desktop from Start menu" -ForegroundColor White
    Write-Host "2. Wait for whale icon to stop spinning" -ForegroundColor White
    Write-Host "3. Run: docker-compose up" -ForegroundColor White
} else {
    Write-Host "Installation may not have completed." -ForegroundColor Yellow
    Write-Host "Please check Docker Desktop in your Start menu." -ForegroundColor Gray
}
