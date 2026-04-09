# Agent Check-in Script - MANDATORY for all agents
# This script MUST be run before any agent action

param(
    [string]$AgentID = "",
    [string]$Action = "",
    [string]$Status = "starting"
)

$LOG_FILE = "S:\TAKE10\logs\agent_log.json"
$ACTIVITY_LOG = "S:\TAKE10\AGENT_ACTIVITY_LOG.md"

# Force agent to read guidelines
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ONEQUEUE AGENT CHECK-IN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  CRITICAL GUIDELINES:" -ForegroundColor Yellow
Write-Host "1. Document EVERY action with timestamp and Agent ID" -ForegroundColor White
Write-Host "2. Store logs LOCALLY, never on VPS" -ForegroundColor White
Write-Host "3. Test before committing" -ForegroundColor White
Write-Host "4. Read ACTIVITY_LOG.md before ANY action" -ForegroundColor White
Write-Host ""

# Check if log exists
if (!(Test-Path $LOG_FILE)) {
    Write-Host "❌ ERROR: Agent log not found!" -ForegroundColor Red
    Write-Host "Creating new log..." -ForegroundColor Yellow
    # Initialize log would go here
    exit 1
}

# Read current log
$log = Get-Content $LOG_FILE -Raw | ConvertFrom-Json

# Display last 3 entries
Write-Host "Recent Activity:" -ForegroundColor Cyan
$log.entries | Select-Object -Last 3 | ForEach-Object {
    Write-Host "  [$($_.id)] $($_.timestamp): $($_.action) by $($_.agent_id)" -ForegroundColor Gray
}
Write-Host ""

# Register this session
$nextId = $log.entries.Count + 1
$entry = @{
    id = $nextId
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    agent_id = $AgentID
    action = $Action
    reason = "Agent session started"
    files_changed = @()
    test_results = "Pending"
    status = $Status
}

Write-Host "Agent $AgentID checked in for: $Action" -ForegroundColor Green
Write-Host "Entry #$nextId created" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Ready to proceed. Remember to:" -ForegroundColor Green
Write-Host "   1. Log EVERY change" -ForegroundColor White
Write-Host "   2. Test before deploying" -ForegroundColor White
Write-Host "   3. Update this log when done" -ForegroundColor White

# Return entry for use in script
return $entry
