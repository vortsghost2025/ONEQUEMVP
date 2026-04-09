# Force Docker Desktop Reinstall
Write-Host "=== Force Docker Desktop Reinstall ===" -ForegroundColor Cyan
Write-Host ""

# Stop any running Docker processes
Write-Host "Stopping Docker processes..." -ForegroundColor Yellow
Get-Process -Name "*docker*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Uninstall existing Docker Desktop
Write-Host "Uninstalling existing Docker Desktop..." -ForegroundColor Yellow
$dockerApp = Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -like "*Docker Desktop*" }
if ($dockerApp) {
    Write-Host "  Uninstalling..." -ForegroundColor Gray
    $dockerApp.Uninstall() | Out-Null
    Write-Host "  Uninstalled" -ForegroundColor Green
} else {
    Write-Host "  No installation found to uninstall" -ForegroundColor Gray
}

# Clean up old files
Write-Host "Cleaning old files..." -ForegroundColor Yellow
$paths = @(
    "C:\Program Files\Docker",
    "C:\ProgramData\Docker",
    "$env:LOCALAPPDATA\Docker",
    "$env:APPDATA\Docker",
    "$env:USERPROFILE\.docker"
)
foreach ($path in $paths) {
    if (Test-Path $path) {
        Write-Host "  Removing: $path" -ForegroundColor Gray
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Fresh install
Write-Host ""
Write-Host "Starting fresh installation..." -ForegroundColor Yellow
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

if (!(Test-Path $installerPath)) {
    Write-Host "  Downloading Docker Desktop..." -ForegroundColor Gray
    $downloadUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
}

Write-Host "  Running installer..." -ForegroundColor Gray
Write-Host "  IMPORTANT: Watch for the Docker Desktop window to appear" -ForegroundColor Yellow
Write-Host "  Accept the license and let it install" -ForegroundColor Yellow
Start-Process $installerPath -ArgumentList "install", "--quiet" -Wait

# Verify
Write-Host ""
Write-Host "Checking installation..." -ForegroundColor Yellow
if (Test-Path "C:\Program Files\Docker\Docker\Docker Desktop.exe") {
    Write-Host "SUCCESS! Docker Desktop installed." -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting Docker Desktop..." -ForegroundColor Cyan
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "Wait for the whale icon in your tray to stop spinning" -ForegroundColor Gray
    Write-Host "Then run: docker-compose up" -ForegroundColor White
} else {
    Write-Host "Installation may need manual completion." -ForegroundColor Yellow
    Write-Host "Please check your Start menu for Docker Desktop." -ForegroundColor Gray
}
