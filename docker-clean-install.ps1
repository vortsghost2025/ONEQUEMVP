# Complete Docker Desktop Clean Install Script
# Run this as Administrator

Write-Host "=== Docker Desktop Complete Removal ===" -ForegroundColor Cyan

# 1. Stop all Docker processes
Write-Host "`n[1/6] Stopping Docker processes..." -ForegroundColor Yellow
$processes = @("Docker Desktop", "Docker Desktop Backend", "com.docker.proxy", "com.docker.supervisor", "com.docker.backend", "com.docker.frontend", "com.docker.launcher", "com.docker.vmnetd", "com.docker.docker-credential-desktop", "com.docker.helper", "qemu-system-x86_64")
foreach ($proc in $processes) {
    Get-Process -Name $proc -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

# Stop Docker service
Stop-Service com.docker.service -Force -ErrorAction SilentlyContinue

# 2. Uninstall via PowerShell
Write-Host "`n[2/6] Uninstalling Docker Desktop..." -ForegroundColor Yellow
$dockerApp = Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -like "*Docker Desktop*" }
if ($dockerApp) {
    $dockerApp.Uninstall()
    Write-Host "✓ Docker Desktop uninstalled" -ForegroundColor Green
} else {
    Write-Host "⚠ Docker Desktop not found in installed programs" -ForegroundColor Yellow
}

# 3. Remove all directories
Write-Host "`n[3/6] Removing Docker directories..." -ForegroundColor Yellow
$pathsToRemove = @(
    "C:\Program Files\Docker",
    "C:\Program Files (x86)\Docker",
    "C:\ProgramData\Docker",
    "C:\ProgramData\DockerDesktop",
    "$env:LOCALAPPDATA\Docker",
    "$env:LOCALAPPDATA\Docker Inc",
    "$env:APPDATA\Docker",
    "$env:APPDATA\Docker Inc",
    "$env:USERPROFILE\.docker",
    "$env:USERPROFILE\AppData\Local\Packages\DockerDesktop*",
    "C:\Users\seand\AppData\Local\Docker",
    "C:\Users\seand\AppData\Roaming\Docker"
)

foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Removed: $path" -ForegroundColor Gray
    }
}

# 4. Clean registry
Write-Host "`n[4/6] Cleaning registry..." -ForegroundColor Yellow
$registryPaths = @(
    "HKLM:\SOFTWARE\Docker Desktop",
    "HKCU:\SOFTWARE\Docker Desktop",
    "HKLM:\SOFTWARE\WOW6432Node\Docker Desktop"
)
foreach ($regPath in $registryPaths) {
    if (Test-Path $regPath) {
        Remove-Item -Path $regPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Removed: $regPath" -ForegroundColor Gray
    }
}

# 5. Remove from PATH
Write-Host "`n[5/6] Cleaning PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$cleanedPath = $currentPath -replace ';C:\\Program Files\\Docker\\Docker\\resources\\bin', '' -replace ';C:\\Program Files\\Docker\\Docker\\resources\\bin\\cli', ''
[Environment]::SetEnvironmentVariable("Path", $cleanedPath, "Machine")
Write-Host "  ✓ PATH cleaned" -ForegroundColor Gray

# 6. Restart computer (required for complete cleanup)
Write-Host "`n[6/6] Cleanup complete!" -ForegroundColor Green
Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Cyan
Write-Host "1. RESTART YOUR COMPUTER (required)" -ForegroundColor Yellow
Write-Host "2. After restart, run: .\docker-fresh-install.ps1" -ForegroundColor Yellow
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
