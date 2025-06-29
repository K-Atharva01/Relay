#!/bin/bash
source "$(dirname "$0")/common.sh"

SENDER_USERNAME=$1
RECIPIENT_USERNAME=$2
MESSAGE_CONTENT=$3

if [ -z "$SENDER_USERNAME" ] || [ -z "$RECIPIENT_USERNAME" ] || [ -z "$MESSAGE_CONTENT" ]; then
    echo "Usage: $0 <sender_username> <recipient_username> \"<message_content>\""
    exit 1
fi

SENDER_ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Sender token not found.")
SENDER_IDENTITY_KEY_UID=$(read_from_tmp "$SENDER_IDENTITY_KEY_UID_FILE" "Sender identity key UID not found.")
RECIPIENT_EPHEMERAL_KEY_UID=$(read_from_tmp "$RECIPIENT_EPHEMERAL_KEY_UID_FILE" "Recipient ephemeral key UID not found.")


echo "--- Sending Message from $SENDER_USERNAME to $RECIPIENT_USERNAME ---"
RESPONSE=$(curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $SENDER_ACCESS_TOKEN" \
    -d "{ \"recipient_username\": \"$RECIPIENT_USERNAME\", \"encrypted_content\": \"$MESSAGE_CONTENT\", \"recipient_key_uid\": \"$RECIPIENT_EPHEMERAL_KEY_UID\", \"sender_signature\": \"$SENDER_MESSAGE_SIGNATURE\", \"sender_public_identity_key_uid\": \"$SENDER_IDENTITY_KEY_UID\" }" \
    "${BASE_URL}/message/send")

echo "$RESPONSE" | jq .

MESSAGE_UID=$(echo "$RESPONSE" | jq -r .message_uid)

if [ -z "$MESSAGE_UID" ] || [ "$MESSAGE_UID" = "null" ]; then
    echo "ERROR: Message send failed."
    exit 1
else
    echo "Message UID: '$MESSAGE_UID'"
    write_to_tmp "$LAST_SENT_MESSAGE_UID_FILE" "$MESSAGE_UID"
    echo "Message UID saved to $LAST_SENT_MESSAGE_UID_FILE"
fi
