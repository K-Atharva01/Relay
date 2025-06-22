#!/bin/bash

TOKEN=$(cat alice.token)
MESSAGE_UID="1"  # Replace with actual UID from inbox

curl -s -G http://localhost:5000/getMessageById \
  --data-urlencode "message_uid=$MESSAGE_UID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
