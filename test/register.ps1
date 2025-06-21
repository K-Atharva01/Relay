# Set the server URL
$baseUrl = "http://127.0.0.1:5000"

# Define user and public key
$username = "alice"
$publicKey = @"
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCsuZSJB5ijTaUyCFtXe6nsxrO55/D+OgzBs3/u0syC
xcSRsg8i/LVafnCt2jf5EXfb/xkyLFfeQY8S7ZtO/AGqXgwg4c9SxIVr4HJWW2ntITd571x+k5kmzEs7
qYQgOy0ycJsuiG39DETSEfr5qP2J8pd4tNwjo6G+8QAB
-----END PUBLIC KEY-----
"@

# Prepare request body
$body = @{
    username = $username
    public_key = $publicKey
} | ConvertTo-Json -Depth 2

# Send the request
$response = Invoke-RestMethod -Uri "$baseUrl/keys/register" -Method Post -Body $body -ContentType "application/json"

# Output
$response
