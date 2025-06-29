#!/bin/bash
source "common.sh"

# User details (can be passed as arguments or modified here)
USERNAME="testuser2"
PASSWORD="securepassword123"
NAME="Test User Two"
PHONE="+919876543211"
EMAIL="test2@example.com"

echo "--- Registering User: $USERNAME : $PASSWORD ---"
curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -d "{ \"name\": \"$NAME\", \"username\": \"$USERNAME\", \"password\": \"$PASSWORD\", \"phone\": \"$PHONE\", \"email\": \"$EMAIL\" }" \
    "${BASE_URL}/auth/register" | jq .
