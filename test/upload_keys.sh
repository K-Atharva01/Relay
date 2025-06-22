#!/bin/bash

BASE_URL="http://localhost:5000"

ALICE_TOKEN=$(cat alice.token)
BOB_TOKEN=$(cat bob.token)

ALICE_KEY="-----BEGIN PUBLIC KEY-----\nALICE_FAKE_KEY\n-----END PUBLIC KEY-----"
BOB_KEY="-----BEGIN PUBLIC KEY-----\nBOB_FAKE_KEY\n-----END PUBLIC KEY-----"

echo "Uploading Alice's public key..."
curl -s -X POST "$BASE_URL/key/upload" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ALICE_TOKEN" \
    -d "{\"public_key\": \"$ALICE_KEY\"}" | jq

echo "Uploading Bob's public key..."
curl -s -X POST "$BASE_URL/key/upload" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BOB_TOKEN" \
    -d "{\"public_key\": \"$BOB_KEY\"}" | jq
