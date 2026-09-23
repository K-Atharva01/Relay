#!/bin/bash

BASE_URL="http://192.168.0.200:5000"
ALICE_TOKEN=$(cat alice.token)

echo "Fetching Bob's latest public key UID..."
RESPONSE=$(curl -s -X POST "$BASE_URL/keys/fetchPublicKey" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ALICE_TOKEN" \
    -d '{"username": "bob"}')

echo "$RESPONSE" | jq
KEY_UID=$(echo "$RESPONSE" | jq -r '.key_uid')

# Save key_uid for next step
echo "$KEY_UID" > bob_key_uid.txt
