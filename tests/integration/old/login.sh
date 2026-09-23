#!/bin/bash

# Usage: ./get_token.sh <username> <password>

BASE_URL="http://192.168.0.200:5000"

USERNAME="$1"
PASSWORD="$2"
OUTPUT_FILE="token_$USERNAME.jwt"

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <username> <password>"
    exit 1
fi

echo "🔐 Logging in as $USERNAME..."

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed for $USERNAME"
    exit 1
fi

echo "✅ Token received:"
echo "$TOKEN"

echo "$TOKEN" > "$OUTPUT_FILE"
echo "💾 Saved to $OUTPUT_FILE"

echo "✏️ You may now manually edit this token to simulate tampering."
