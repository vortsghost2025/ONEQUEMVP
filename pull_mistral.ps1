$body = '{"model":"mistral"}'
$response = Invoke-RestMethod -Uri 'http://localhost:9001/api/pull' -Method Post -Body $body -ContentType 'application/json' -Stream
while ($true) {
    $line = $response.ReadLine()
    if ($line) { $line } else { break }
}
$response.Close()