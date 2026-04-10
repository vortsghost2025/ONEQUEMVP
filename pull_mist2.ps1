# Try pulling mistral
$body = '{"model":"mistral"}'
$response = Invoke-RestMethod -Uri 'http://localhost:9001/api/pull' -Method Post -Body $body -ContentType 'application/json'
$response