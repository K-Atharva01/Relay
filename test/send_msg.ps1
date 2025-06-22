$token = "<paste-access-token-here>"

$headers = @{
    Authorization = "Bearer $token"
}

$body = @{
    recipient = "bob"
    message = "ENCRYPTED_MESSAGE_DATA"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:5000/messages/send -Method POST -Body $body -Headers $headers -ContentType "application/json"
