#!/bin/bash

BASE_URL="http://localhost:5000"

echo "Logging in Alice..."
ALICE_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "alicepass"}' | jq -r '.access_token')

echo "Logging in Bob..."
BOB_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "bob", "password": "bobpass"}' | jq -r '.access_token')

echo "Alice Token: $ALICE_TOKEN"
echo "Bob Token: $BOB_TOKEN"

# Save tokens to file for other scripts
echo "$ALICE_TOKEN" > alice.token
echo "$BOB_TOKEN" > bob.token
