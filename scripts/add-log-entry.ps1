# Add Log Entry Script - Use for EVERY change
param(
    [string]$AgentID = "",
    [string]$Action = "",
    [string]$Reason = "",
    [string]$Files = "",
    [string]$TestResults = "Pending",
    [string]$Status = "in_progress"
)

$LOG_FILE = "S:\TAKE10\logs\agent_log.json"
$ACTIVITY_LOG = "S:\TAKE10\AGENT_ACTIVITY_LOG.md"

# Read current log
$log = Get-Content $LOG_FILE -Raw | ConvertFrom-Json

# Create new entry
$nextId = $log.entries.Count + 1
$newEntry = @{
    id = $nextId
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    agent_id = $AgentID
    action = $Action
    reason = $Reason
    files_changed = $Files.Split(",") | ForEach-Object { $_.Trim() }
    test_results = $TestResults
    status = $Status
}

# Add to log
$log.entries += $newEntry
$log.total_entries = $log.entries.Count
$log.last_updated = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# Save JSON log
$log | ConvertTo-Json -Depth 10 | Set-Content $LOG_FILE

# Add to markdown log
$mdEntry = @"

### Entry #$nextId
- **Timestamp:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")
- **Agent ID:** $AgentID
- **Action:** $Action
- **Reason:** $Reason
- **Files Changed:** $($Files)
- **Test Results:** $TestResults
- **Status:** $Status

"@

Add-Content $ACTIVITY_LOG $mdEntry

Write-Host "✅ Log entry #$nextId added" -ForegroundColor Green
Write-Host "   Agent: $AgentID" -ForegroundColor Gray
Write-Host "   Action: $Action" -ForegroundColor Gray
Write-Host "   Status: $Status" -ForegroundColor Gray
