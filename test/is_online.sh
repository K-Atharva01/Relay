#!/bin/bash

# --- Configuration ---
BASE_URL="http://192.168.0.200:5000"
IS_ONLINE_URL_TEMPLATE="${BASE_URL}/user/isOnline"

# --- User Input ---
read -p "Enter the username to check (e.g., testuser1): " TARGET_USERNAME

YOUR_JWT_TOKEN=$(cat test_token)

# --- Make the API Request ---
echo "--- Checking online status for ${TARGET_USERNAME} ---"

# Construct the URL
API_URL="${IS_ONLINE_URL_TEMPLATE}/${TARGET_USERNAME}"

# Make the GET request with the Authorization header
response=$(curl -s -X GET \
  -H "Authorization: Bearer ${YOUR_JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  "${API_URL}")

# Check if the request was successful and print the response
if [ $? -eq 0 ]; then
  echo "API Response:"
  echo "$response" | jq . # Pretty print the JSON response using jq
else
  echo "Error: curl command failed."
fi

echo "--- Request Complete ---"
