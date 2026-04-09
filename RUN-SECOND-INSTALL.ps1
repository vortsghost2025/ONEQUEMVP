# Docker Clean Install - Step 2 of 2
# This installs fresh Docker Desktop

Write-Host "Downloading Docker Desktop..." -ForegroundColor Yellow

# Download installer
$downloadUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "Download complete!" -ForegroundColor Green
} catch {
    Write-Host "Download failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
Start-Process $installerPath -ArgumentList "install", "--quiet" -Wait

Write-Host "" -ForegroundColor White
Write-Host "STEP 2 DONE!" -ForegroundColor Green
Write-Host "Docker Desktop is installed!" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "Next: Open Docker Desktop from Start menu" -ForegroundColor Yellow
Write-Host "Then run: S:\TAKE10\RUN-THIRD-SETUP.ps1" -ForegroundColor White
