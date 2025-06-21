#!/bin/bash

# Base URL
BASE_URL="http://127.0.0.1:5000"

# Sender, Receiver and Encrypted Message
SENDER="alice"
RECEIVER="bob"
ENC_MSG=$(echo -n "This is a secret message" | base64)

echo "📤 Sending encrypted message from $SENDER to $RECEIVER..."

curl -s -X POST "$BASE_URL/messages/send" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "sender": "$SENDER",
  "receiver": "$RECEIVER",
  "message": "$ENC_MSG"
}
EOF

echo -e "\n✅ Message sent."
