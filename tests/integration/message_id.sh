#!/bin/bash

TOKEN=$(cat bob.token)
MESSAGE_UID="REPLACE_WITH_UUID_FROM_INBOX"  # e.g. from GET /message/inbox

curl -X POST http://192.168.0.200:5000/message/getMessageById \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message_uid\": \"$MESSAGE_UID\"}"
