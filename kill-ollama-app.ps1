# Run this as Administrator to kill Ollama Snowman app
# The app polls localhost:11434/api/tags every 31 seconds
# This is normal UI refresh behavior but can be stopped

Write-Host "Killing Ollama Snowman app (PID 36248)..." -ForegroundColor Yellow
try {
    Stop-Process -Id 36248 -Force -ErrorAction Stop
    Write-Host "SUCCESS: Ollama Snowman app killed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Access denied. Please run as Administrator" -ForegroundColor Red
    exit 1
}

Write-Host "`nOllama server processes still running:" -ForegroundColor Cyan
Get-Process | Where-Object { $_.ProcessName -like '*ollama*' } | Format-Table Name, Id, CPU -AutoSize

Write-Host "`nTo prevent auto-start of Ollama app:" -ForegroundColor Yellow
Write-Host "  1. Open Task Manager -> Startup apps" -ForegroundColor White
Write-Host "  2. Disable 'Ollama' if present" -ForegroundColor White
Write-Host "  3. Or uninstall Ollama app from Settings -> Apps" -ForegroundColor White
