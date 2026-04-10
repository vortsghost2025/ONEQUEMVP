$body = @{
    model = "phi3"
    messages = @(
        @{
            role = "user"
            content = "What is 2 + 2? Show your reasoning."
        }
    )
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:9001/api/chat" -Method Post -Body $body -ContentType "application/json"
$response.message.content