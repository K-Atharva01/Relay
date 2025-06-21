#!/bin/bash

# Base URL
BASE_URL="http://127.0.0.1:5000"

# Username whose public key you want
USERNAME="alice"

echo "🔑 Fetching public key for $USERNAME..."

curl -s -X GET "$BASE_URL/keys/$USERNAME" \
  -H "Accept: application/json"

echo -e "\n✅ Public key fetched."
