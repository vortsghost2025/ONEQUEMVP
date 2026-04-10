# Test if deepseek-coder supports tools
$body = '{
  "model": "deepseek-coder:latest",
  "messages": [{"role": "user", "content": "Hello"}],
  "tools": [{"type": "function", "function": {"name": "test", "parameters": {"type": "object", "properties": {"arg": {"type": "string"}}}} }]
}'
$response = Invoke-RestMethod -Uri 'http://localhost:9001/api/chat' -Method Post -Body $body -ContentType 'application/json'
$response