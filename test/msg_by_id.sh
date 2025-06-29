#!/bin/bash
source "$(dirname "$0")/common.sh"

RECIPIENT_USERNAME=$1
MESSAGE_UID=$2 # Can be passed as arg or read from LAST_SENT_MESSAGE_UID_FILE

if [ -z "$RECIPIENT_USERNAME" ]; then
    echo "Usage: $0 <recipient_username> [message_uid]"
    exit 1
fi

# If message_uid is not provided as argument, try to read from temp file
if [ -z "$MESSAGE_UID" ]; then
    MESSAGE_UID=$(read_from_tmp "$LAST_SENT_MESSAGE_UID_FILE" "No message UID found. Send a message first or provide UID.")
fi

ACCESS_TOKEN=""
if [ "$RECIPIENT_USERNAME" == "testuser1" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$SENDER_TOKEN_FILE" "Sender token not found.")
elif [ "$RECIPIENT_USERNAME" == "testuser2" ]; then
    ACCESS_TOKEN=$(read_from_tmp "$RECIPIENT_TOKEN_FILE" "Recipient token not found.")
else
    echo "Error: Unknown username."
    exit 1
fi

echo "--- Getting Message by UID ($MESSAGE_UID) for $RECIPIENT_USERNAME ---"
curl $CURL_POST_COMMON_OPTS \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{ \"message_uid\": \"$MESSAGE_UID\" }" \
    "${BASE_URL}/message/getMessageById" | jq .
