$body = @{
    model = "phi3"
    messages = @(
        @{
            role = "user"
            content = "What files are in the current directory? Use the tool to list them."
        }
    )
    tools = @(
        @{
            type = "function"
            function = @{
                name = "filesystem_list_directory"
                description = "Get a detailed listing of all files and directories in a specified path"
                parameters = @{
                    type = "object"
                    properties = @{
                        path = @{
                            type = "string"
                            description = "The path to list"
                        }
                    }
                    required = @("path")
                }
            }
        }
    )
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri "http://localhost:9001/api/chat" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 5