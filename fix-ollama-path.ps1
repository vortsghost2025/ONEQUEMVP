# Run this in ADMIN PowerShell
# Sets OLLAMA_MODELS to centralized location

$ollamaPath = "S:\Ollama\data\.ollama\models"

# Create directory if needed
if (-not (Test-Path $ollamaPath)) {
    New-Item -ItemType Directory -Path $ollamaPath -Force | Out-Null
    Write-Host "Created: $ollamaPath" -ForegroundColor Green
}

# Set system-wide environment variable (requires admin)
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ollamaPath, "Machine")
Write-Host "Set OLLAMA_MODELS system-wide to: $ollamaPath" -ForegroundColor Green

# Also set for current session
$env:OLLAMA_MODELS = $ollamaPath
Write-Host "Set for current session" -ForegroundColor Green

Write-Host "`nRestart Ollama for changes to take effect" -ForegroundColor Yellow
Write-Host "All agents will now use: $ollamaPath" -ForegroundColor Cyan
