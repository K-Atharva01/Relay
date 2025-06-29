#!/bin/bash
source "$(dirname "$0")/common.sh"

USERNAME=$1
PASSWORD=$2 # Use provided password

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <username> <password>"
    exit 1
fi

TOKEN_FILE=""
if [ "$USERNAME" == "testuser1" ]; then
    TOKEN_FILE="$SENDER_TOKEN_FILE"
elif [ "$USERNAME" == "testuser2" ]; then
    TOKEN_FILE="$RECIPIENT_TOKEN_FILE"
else
    echo "Error: Unknown username for token storage."
    exit 1
fi

echo "--- Logging in User: $USERNAME ---"
RESPONSE=$(curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -d "{ \"username\": \"$USERNAME\", \"password\": \"$PASSWORD\" }" \
    "${BASE_URL}/auth/login")

echo "$RESPONSE" | jq .

ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r .access_token)

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "ERROR: Login failed or token not found for $USERNAME."
    exit 1
else
    echo "Access Token for $USERNAME: '$ACCESS_TOKEN'"
    write_to_tmp "$TOKEN_FILE" "$ACCESS_TOKEN"
    echo "Token saved to $TOKEN_FILE"
fi

