$body = @{
    username = "alice"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:5000/auth/login -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 100 | Out-File -FilePath test.txt -Encoding UTF8