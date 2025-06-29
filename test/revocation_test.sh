#!/bin/bash

# --- Configuration ---
BASE_URL="http://192.168.0.200:5000" # Your Flask server's base URL
PROTECTED_ENDPOINT="${BASE_URL}/message/sendTo" # Example protected GET endpoint

# --- Main Logic ---

# Check if a token was provided as an argument
#if [ -z "$1" ]; then
#    echo "Usage: ./access_endpoint.sh <your_jwt_token>"
#    echo "Example: ./access_endpoint.sh eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
#    exit 1
#fi

TOKEN=$(cat test_token)

echo "--- Attempting to access '$PROTECTED_ENDPOINT' with provided token ---"

# Use curl to make the GET request
# -s: Silent mode (don't show progress meter or error messages)
# -D -: Dump headers to stdout
# -w "%{http_code}\n": Write HTTP status code to stdout after request
# -o /dev/null: Discard the response body to get headers only first, then get body separately
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    -H "Authorization: Bearer $TOKEN" \
    "$PROTECTED_ENDPOINT")

# Get the full response body
RESPONSE_BODY=$(curl -s -X GET \
    -H "Authorization: Bearer $TOKEN" \
    "$PROTECTED_ENDPOINT")

echo "HTTP Status Code: $HTTP_STATUS"
echo "Response Body:"
echo "$RESPONSE_BODY" | jq . # Use jq to pretty-print if it's JSON, otherwise prints as is.

# Optional: Add a simple check for 200 OK or 401 Unauthorized
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo -e "\nAccess successful (200 OK)."
elif [ "$HTTP_STATUS" -eq 401 ]; then
    echo -e "\nAccess denied (401 Unauthorized). Token might be invalid or revoked."
else
    echo -e "\nReceived status code: $HTTP_STATUS"
fi
