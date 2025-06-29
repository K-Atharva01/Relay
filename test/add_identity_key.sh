#!/bin/bash
source "$(dirname "$0")/common.sh"

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username>"
    exit 1
fi

ACCESS_TOKEN=""
KEY_UID_FILE=""
KEY_PEM=""

if [ "$USERNAME" == "testuser1" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Sender token not found. Please run login_user.sh for testuser1 first.")
    KEY_UID_FILE="$SENDER_IDENTITY_KEY_UID_FILE"
    KEY_PEM="$SENDER_IDENTITY_PUBLIC_KEY_PEM"
elif [ "$USERNAME" == "testuser2" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$RECIPIENT_TOKEN_FILE" "Recipient token not found. Please run login_user.sh for testuser2 first.")
    KEY_UID_FILE="$RECIPIENT_IDENTITY_KEY_UID_FILE"
    KEY_PEM="$RECIPIENT_IDENTITY_PUBLIC_KEY_PEM"
else
    echo "Error: Unknown username for key storage."
    exit 1
fi

echo "--- Adding Identity Key for $USERNAME ---"
RESPONSE=$(curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{ \"public_key_pem\": \"$KEY_PEM\", \"key_type\": \"identity\" }" \
    "${BASE_URL}/keys/addKey")

echo "$RESPONSE" | jq .

KEY_UID=$(echo "$RESPONSE" | jq -r .key_uid)

if [ -z "$KEY_UID" ] || [ "$KEY_UID" = "null" ]; then
    echo "ERROR: Identity key upload failed for $USERNAME."
    exit 1
else
    echo "Identity Key UID for $USERNAME: '$KEY_UID'"
    write_to_tmp "$KEY_UID_FILE" "$KEY_UID"
    echo "Key UID saved to $KEY_UID_FILE"
fi
