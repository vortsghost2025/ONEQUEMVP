# Fresh Docker Desktop Install Script
# Run AFTER clean uninstall script and restart

Write-Host "=== Docker Desktop Fresh Install ===" -ForegroundColor Cyan

# 1. Check if already installed
Write-Host "`n[1/5] Checking existing installation..." -ForegroundColor Yellow
$dockerExe = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerExe) {
    Write-Host "⚠ Docker already installed at: $($dockerExe.Source)" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') { exit }
}

# 2. Download Docker Desktop
Write-Host "`n[2/5] Downloading Docker Desktop..." -ForegroundColor Yellow
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"

try {
    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
    Write-Host "✓ Downloaded Docker Desktop Installer" -ForegroundColor Green
} catch {
    Write-Host "✗ Download failed: $_" -ForegroundColor Red
    exit 1
}

# 3. Install with recommended settings
Write-Host "`n[3/5] Installing Docker Desktop..." -ForegroundColor Yellow
Write-Host "This will open the Docker installer. Follow these settings:" -ForegroundColor Cyan
Write-Host "  ✓ Use WSL 2 instead of Hyper-V" -ForegroundColor Gray
Write-Host "  ✓ Add shortcut to desktop" -ForegroundColor Gray
Write-Host "  ✓ Add to PATH (optional)" -ForegroundColor Gray
Write-Host "`nStarting installer..." -ForegroundColor Yellow

# Run installer
Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait

# 4. Verify installation
Write-Host "`n[4/5] Verifying installation..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Docker installation may have issues" -ForegroundColor Red
}

docker-compose --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker Compose installed" -ForegroundColor Green
}

# 5. Configure Docker
Write-Host "`n[5/5] Initial configuration..." -ForegroundColor Yellow

# Create default settings
$dockerConfig = "$env:USERPROFILE\.docker"
if (!(Test-Path $dockerConfig)) {
    New-Item -ItemType Directory -Path $dockerConfig | Out-Null
}

# Set resource limits (conservative for start)
$daemonConfig = @{
    "registry-mirrors" = @()
    "insecure-registries" = @()
    "debug" = $false
    "experimental" = $false
    "features" = @{
        "buildkit" = $true
    }
}

# Start Docker Desktop
Write-Host "`nStarting Docker Desktop for first time..." -ForegroundColor Yellow
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "✓ Docker Desktop starting..." -ForegroundColor Green

Write-Host "`n=== INSTALLATION COMPLETE ===" -ForegroundColor Cyan
Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Wait for Docker Desktop to fully start (whale icon in tray)" -ForegroundColor Gray
Write-Host "2. Run: docker run hello-world" -ForegroundColor Gray
Write-Host "3. Then run: .\docker-setup-onequeue.ps1" -ForegroundColor Gray
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
