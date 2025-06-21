#!/bin/bash

# Base URL
BASE_URL="http://127.0.0.1:5000"

# Username whose inbox you want to fetch
USERNAME="bob"

echo "📥 Fetching inbox for $USERNAME..."

curl -s -X GET "$BASE_URL/messages/inbox/$USERNAME" \
  -H "Accept: application/json"

echo -e "\n✅ Inbox fetched."
