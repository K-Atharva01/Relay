#!/bin/bash
source "$(dirname "$0")/common.sh"

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username>"
    exit 1
fi

ACCESS_TOKEN=""
TOKEN_FILE=""
if [ "$USERNAME" == "testuser1" ]; then
    TOKEN_FILE="$SENDER_TOKEN_FILE"
    ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Sender token not found. Already logged out?")
elif [ "$USERNAME" == "testuser2" ]; then
    TOKEN_FILE="$RECIPIENT_TOKEN_FILE"
    ACCESS_TOKEN=$(read_from_tmp "$RECIPIENT_TOKEN_FILE" "Recipient token not found. Already logged out?")
else
    echo "Error: Unknown username."
    exit 1
fi

echo "--- Logging out User: $USERNAME ---"
curl $CURL_POST_COMMON_OPTS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "${BASE_URL}/auth/logout" | jq .

# Optionally clean up the token file after logout
rm -f "$TOKEN_FILE"
echo "Removed token file: $TOKEN_FILE"
