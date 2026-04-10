$body = @{
    model = "phi3"
    messages = @(
        @{
            role = "user"
            content = "What is the weather in New York? Use the get_weather function."
        }
    )
    tools = @(
        @{
            type = "function"
            function = @{
                name = "get_weather"
                description = "Get weather information for a location"
                parameters = @{
                    type = "object"
                    properties = @{
                        location = @{
                            type = "string"
                            description = "City name"
                        }
                    }
                    required = @("location")
                }
            }
        }
    )
} | ConvertTo-Json -Depth 4

$response = Invoke-RestMethod -Uri "http://localhost:9001/api/chat" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 4