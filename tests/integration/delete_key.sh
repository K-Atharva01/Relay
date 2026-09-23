#!/bin/bash

# Configuration
API_URL="http://localhost:5000/keys/delete"
TOKEN=$(cat bob.token)
KEY_UID="1"  # Replace with a valid key_uid

# Make the request
curl -X POST "$API_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"key_uid\": \"$KEY_UID\"}"

