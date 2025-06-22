#!/bin/bash

BASE_URL="http://localhost:5000"
BOB_TOKEN=$(cat bob.token)

echo "Fetching Bob's inbox..."
curl -s -X GET "$BASE_URL/message/inbox" \
    -H "Authorization: Bearer $BOB_TOKEN" | jq
