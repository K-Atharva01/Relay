#!/bin/bash
source "$(dirname "$0")/common.sh"

CALLER_USERNAME=$1
RECIPIENT_USERNAME=$2
KEY_TYPE=$3 # 'identity' or 'ephemeral'

if [ -z "$CALLER_USERNAME" ] || [ -z "$RECIPIENT_USERNAME" ] || [ -z "$KEY_TYPE" ]; then
    echo "Usage: $0 <caller_username> <recipient_username> <key_type>"
    exit 1
fi

ACCESS_TOKEN=""
if [ "$CALLER_USERNAME" == "testuser1" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Caller token not found. Please run login_user.sh first.")
elif [ "$CALLER_USERNAME" == "testuser2" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$RECIPIENT_TOKEN_FILE" "Caller token not found. Please run login_user.sh first.")
else
    echo "Error: Unknown caller username."
    exit 1
fi

echo "--- Fetching ${KEY_TYPE} Key for ${RECIPIENT_USERNAME} by ${CALLER_USERNAME} ---"
curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{ \"username\": \"$RECIPIENT_USERNAME\", \"key_type\": \"$KEY_TYPE\" }" \
    "${BASE_URL}/keys/fetchPublicKey" | jq .
