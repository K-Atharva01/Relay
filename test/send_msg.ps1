# Set the server URL
$baseUrl = "http://127.0.0.1:5000"

# Define sender, receiver, and message
$body = @{
    sender = "alice"
    receiver = "bob"
    message = "VGhpcyBpcyBhIHNlY3JldCBtZXNzYWdlIQ=="  # Base64 of: This is a secret message!
} | ConvertTo-Json -Depth 2

# Send the request
$response = Invoke-RestMethod -Uri "$baseUrl/messages/send" -Method Post -Body $body -ContentType "application/json"

# Output
$response
