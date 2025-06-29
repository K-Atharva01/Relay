#!/bin/bash
source "$(dirname "$0")/common.sh"

USERNAME=$1
KEY_UID=$2

if [ -z "$USERNAME" ] || [ -z "$KEY_UID" ]; then
    echo "Usage: $0 <username> <key_uid>"
    exit 1
fi

ACCESS_TOKEN=""
if [ "$USERNAME" == "testuser1" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Sender token not found. Please run login_user.sh first.")
elif [ "$USERNAME" == "testuser2" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$RECIPIENT_TOKEN_FILE" "Recipient token not found. Please run login_user.sh first.")
else
    echo "Error: Unknown username."
    exit 1
fi

echo "--- Deleting Key for $USERNAME (UID: $KEY_UID) ---"
curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{ \"key_uid\": \"$KEY_UID\" }" \
    "${BASE_URL}/keys/deleteKey" | jq .

