#!/bin/bash

TOKEN=$(cat bob.token)
MESSAGE_UID="1"  # Replace with actual UID from inbox

curl -X POST http://192.168.0.200:5000/message/inbox/deleteMessage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message_uid\": \"$MESSAGE_UID\"}"
