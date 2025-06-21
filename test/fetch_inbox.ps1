# Set the server URL
$baseUrl = "http://127.0.0.1:5000"

# Target user to fetch inbox
$username = "bob"

# Fetch inbox
$response = Invoke-RestMethod -Uri "$baseUrl/messages/inbox/$username" -Method Get -Headers @{Accept="application/json"}

# Output
$response
