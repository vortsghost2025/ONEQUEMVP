# Docker Clean Install - Step 1 of 2
# This removes old Docker completely

Write-Host "Stopping Docker..." -ForegroundColor Yellow
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Stop-Service com.docker.service -Force -ErrorAction SilentlyContinue

Write-Host "Removing old files..." -ForegroundColor Yellow
Remove-Item "C:\Program Files\Docker" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Docker" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:APPDATA\Docker" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.docker" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Cleaning complete!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "STEP 1 DONE!" -ForegroundColor Cyan
Write-Host "Now RESTART your computer" -ForegroundColor Yellow
Write-Host "After restart, run: S:\TAKE10\RUN-SECOND-INSTALL.ps1" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Press any key to see restart reminder..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Remind to restart
Write-Host "`nREMEMBER: Restart your computer now!" -ForegroundColor Red
Write-Host "Then run the second script: S:\TAKE10\RUN-SECOND-INSTALL.ps1" -ForegroundColor White
