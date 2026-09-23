#!/bin/bash

# Configuration
API_URL="http://localhost:5000/keys/deleteKey"
TOKEN=$(cat bob.token)
KEY_UID="USER_UNIQUE_ID-KEY_ID"  # Replace with a valid key_uid (e.g. from /keys/addKey response)

# Make the request
curl -X POST "$API_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"key_uid\": \"$KEY_UID\"}"

