#!/bin/bash
source "$(dirname "$0")/common.sh"

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username>"
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

echo "--- Getting User List for $USERNAME ---"
curl $CURL_GET_COMMON_OPTS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "${BASE_URL}/message/sendTo" | jq .
