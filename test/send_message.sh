#!/bin/bash

BASE_URL="http://localhost:5000"
ALICE_TOKEN=$(cat alice.token)
BOB_KEY_UID=$(cat bob_key_uid.txt)

# Simulated encrypted message
ENC_MSG="gAAAAFakeEncryptedMessageToBob"

echo "Sending encrypted message to Bob..."
curl -s -X POST "$BASE_URL/message/send" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ALICE_TOKEN" \
    -d "{\"recipient\": \"bob\", \"message\": \"$ENC_MSG\", \"key_uid\": \"$BOB_KEY_UID\"}" | jq
