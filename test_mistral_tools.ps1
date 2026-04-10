# Test if mistral supports tools
$body = '{
  "model": "mistral",
  "messages": [{"role": "user", "content": "Hello"}],
  "tools": [{"type": "function", "function": {"name": "test", "parameters": {"type": "object", "properties": {"arg": {"type": "string"}}}} }]
}'
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:9001/api/chat' -Method Post -Body $body -ContentType 'application/json' -ErrorAction Stop
    $response | ConvertTo-Json
    Write-Host "SUCCESS: mistral supports tools!"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}