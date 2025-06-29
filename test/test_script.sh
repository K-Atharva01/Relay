#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Print commands and their arguments as they are executed. (Keep this on!)
set -x

# --- Configuration ---
BASE_URL="http://192.168.0.200:5000" # Ensure this is correct
CURL_POST_COMMON_OPTS="-v -X POST" # Added -v, Removed -s for debugging POST requests
CURL_GET_COMMON_OPTS="-v -X GET"   # Added -v, Removed -s for debugging GET requests

# --- User 1 (Sender) ---
SENDER_USERNAME="testuser1"
SENDER_PASSWORD="securepassword123"
SENDER_NAME="Test User One"
SENDER_PHONE="+919876543210"
SENDER_EMAIL="test1@example.com"
SENDER_ACCESS_TOKEN=""
SENDER_IDENTITY_KEY_UID=""
SENDER_EPHEMERAL_KEY_UID=""

# Placeholder for actual PEM public keys and signatures.
SENDER_IDENTITY_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nSENDER_IDENTITY_PUB_KEY_PLACEHOLDER_1\n-----END PUBLIC KEY-----"
SENDER_EPHEMERAL_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nSENDER_EPHEMERAL_PUB_KEY_PLACEHOLDER_1\n-----END PUBLIC KEY-----"
SENDER_MESSAGE_SIGNATURE="SENDER_SIGNATURE_FOR_MESSAGE_PLACEHOLDER"


# --- User 2 (Recipient) ---
RECIPIENT_USERNAME="testuser2"
RECIPIENT_PASSWORD="anotherpassword456"
RECIPIENT_NAME="Test User Two"
RECIPIENT_PHONE="+919988776655"
RECIPIENT_EMAIL="test2@example.com"
RECIPIENT_ACCESS_TOKEN=""
RECIPIENT_IDENTITY_KEY_UID=""
RECIPIENT_EPHEMERAL_KEY_UID=""

RECIPIENT_IDENTITY_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nRECIPIENT_IDENTITY_PUB_KEY_PLACEHOLDER_2\n-----END PUBLIC KEY-----"
RECIPIENT_EPHEMERAL_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nRECIPIENT_EPHEMERAL_PUB_KEY_PLACEHOLDER_2\n-----END PUBLIC KEY-----"


# --- Functions for API Calls ---

# NO CHANGE TO REGISTER/LOGIN FUNCTIONS, AS THEY WORKED.
# But they will now output verbose curl details due to CURL_POST_COMMON_OPTS change.
function register_user() {
    local username=$1
    local password=$2
    local name=$3
    local phone=$4
    local email=$5
    echo "Registering user: $username"
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -d "{ \"name\": \"$name\", \"username\": \"$username\", \"password\": \"$password\", \"phone\": \"$phone\", \"email\": \"$email\" }" \
        "${BASE_URL}/auth/register" | jq .
}

function login_user() {
    local username=$1
    local password=$2
    echo "Logging in user: $username"
    RESPONSE=$(curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -d "{ \"username\": \"$username\", \"password\": \"$password\" }" \
        "${BASE_URL}/auth/login")
    echo "$RESPONSE" | jq .
    # Extract token; ensure the variable is properly quoted when returned
    echo "$RESPONSE" | jq -r .access_token
}

# --- Functions that were failing, now with verbose curl output ---
function add_key() {
    local token=$1
    local public_key_pem=$2
    local key_type=$3
    echo "Adding ${key_type} key..."
    RESPONSE=$(curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"public_key_pem\": \"$public_key_pem\", \"key_type\": \"$key_type\" }" \
        "${BASE_URL}/keys/addKey")
    echo "$RESPONSE" | jq .
    echo "$RESPONSE" | jq -r .key_uid
}

function get_all_keys() {
    local token=$1
    echo "Getting all keys..."
    curl $CURL_GET_COMMON_OPTS \
        -H "Authorization: Bearer $token" \
        "${BASE_URL}/keys/getAllKeys" | jq .
}

function fetch_public_key() {
    local token=$1
    local recipient_username=$2
    local key_type=$3
    echo "Fetching ${key_type} key for ${recipient_username}..."
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"username\": \"$recipient_username\", \"key_type\": \"$key_type\" }" \
        "${BASE_URL}/keys/fetchPublicKey" | jq .
}

function delete_key() {
    local token=$1
    local key_uid=$2
    echo "Deleting key: ${key_uid}..."
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"key_uid\": \"$key_uid\" }" \
        "${BASE_URL}/keys/deleteKey" | jq .
}

function get_user_list() {
    local token=$1
    echo "Getting user list..."
    curl $CURL_GET_COMMON_OPTS \
        -H "Authorization: Bearer $token" \
        "${BASE_URL}/message/sendTo" | jq .
}

function send_message() {
    local token=$1
    local recipient_username=$2
    local message_content=$3
    local recipient_key_uid=$4
    local sender_signature=$5
    local sender_identity_key_uid=$6
    echo "Sending message to ${recipient_username}..."
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"recipient_username\": \"$recipient_username\", \"encrypted_content\": \"$message_content\", \"recipient_key_uid\": \"$recipient_key_uid\", \"sender_signature\": \"$sender_signature\", \"sender_public_identity_key_uid\": \"$sender_identity_key_uid\" }" \
        "${BASE_URL}/message/send" | jq .
}

function get_inbox() {
    local token=$1
    echo "Getting inbox messages..."
    curl $CURL_GET_COMMON_OPTS \
        -H "Authorization: Bearer $token" \
        "${BASE_URL}/message/inbox" | jq .
}

function get_message_by_id() {
    local token=$1
    local message_uid=$2
    echo "Getting message by UID: ${message_uid}..."
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"message_uid\": \"$message_uid\" }" \
        "${BASE_URL}/message/getMessageById" | jq .
}

function delete_message() {
    local token=$1
    local message_uid=$2
    echo "Deleting message by UID: ${message_uid}..."
    curl $CURL_POST_COMMON_OPTS \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "{ \"message_uid\": \"$message_uid\" }" \
        "${BASE_URL}/message/inbox/deleteMessage" | jq .
}


# --- Test Execution (No changes here, as functions are called) ---

echo "--- Starting API Tests ---"

echo ""
echo "--- 1. Register Sender User ---"
register_user "$SENDER_USERNAME" "$SENDER_PASSWORD" "$SENDER_NAME" "$SENDER_PHONE" "$SENDER_EMAIL"

echo ""
echo "--- 2. Register Recipient User ---"
register_user "$RECIPIENT_USERNAME" "$RECIPIENT_PASSWORD" "$RECIPIENT_NAME" "$RECIPIENT_PHONE" "$RECIPIENT_EMAIL"


echo ""
echo "--- 3. Sender Login ---"
SENDER_ACCESS_TOKEN=$(login_user "$SENDER_USERNAME" "$SENDER_PASSWORD")
echo "Sender Access Token: '${SENDER_ACCESS_TOKEN}'" # Added quotes for debug clarity
if [ -z "$SENDER_ACCESS_TOKEN" ] || [ "$SENDER_ACCESS_TOKEN" = "null" ]; then echo "ERROR: Sender login failed or token not found."; exit 1; fi

echo ""
echo "--- 4. Recipient Login ---"
RECIPIENT_ACCESS_TOKEN=$(login_user "$RECIPIENT_USERNAME" "$RECIPIENT_PASSWORD")
echo "Recipient Access Token: '${RECIPIENT_ACCESS_TOKEN}'" # Added quotes for debug clarity
if [ -z "$RECIPIENT_ACCESS_TOKEN" ] || [ "$RECIPIENT_ACCESS_TOKEN" = "null" ]; then echo "ERROR: Recipient login failed or token not found."; exit 1; fi


echo ""
echo "--- 5. Sender Adds Identity Key ---"
SENDER_IDENTITY_KEY_UID=$(add_key "$SENDER_ACCESS_TOKEN" "$SENDER_IDENTITY_PUBLIC_KEY_PEM" "identity")
echo "Sender Identity Key UID: '${SENDER_IDENTITY_KEY_UID}'"
if [ -z "$SENDER_IDENTITY_KEY_UID" ] || [ "$SENDER_IDENTITY_KEY_UID" = "null" ]; then echo "ERROR: Sender identity key upload failed."; exit 1; fi

echo ""
echo "--- 6. Sender Adds Ephemeral Key ---"
SENDER_EPHEMERAL_KEY_UID=$(add_key "$SENDER_ACCESS_TOKEN" "$SENDER_EPHEMERAL_PUBLIC_KEY_PEM" "ephemeral")
echo "Sender Ephemeral Key UID: '${SENDER_EPHEMERAL_KEY_UID}'"
if [ -z "$SENDER_EPHEMERAL_KEY_UID" ] || [ "$SENDER_EPHEMERAL_KEY_UID" = "null" ]; then echo "ERROR: Sender ephemeral key upload failed."; exit 1; fi


echo ""
echo "--- 7. Recipient Adds Identity Key ---"
RECIPIENT_IDENTITY_KEY_UID=$(add_key "$RECIPIENT_ACCESS_TOKEN" "$RECIPIENT_IDENTITY_PUBLIC_KEY_PEM" "identity")
echo "Recipient Identity Key UID: '${RECIPIENT_IDENTITY_KEY_UID}'"
if [ -z "$RECIPIENT_IDENTITY_KEY_UID" ] || [ "$RECIPIENT_IDENTITY_KEY_UID" = "null" ]; then echo "ERROR: Recipient identity key upload failed."; exit 1; fi

echo ""
echo "--- 8. Recipient Adds Ephemeral Key (Crucial for receiving encrypted messages) ---"
RECIPIENT_EPHEMERAL_KEY_UID=$(add_key "$RECIPIENT_ACCESS_TOKEN" "$RECIPIENT_EPHEMERAL_PUBLIC_KEY_PEM" "ephemeral")
echo "Recipient Ephemeral Key UID: '${RECIPIENT_EPHEMERAL_KEY_UID}'"
if [ -z "$RECIPIENT_EPHEMERAL_KEY_UID" ] || [ "$RECIPIENT_EPHEMERAL_KEY_UID" = "null" ]; then echo "ERROR: Recipient ephemeral key upload failed."; exit 1; fi


echo ""
echo "--- 9. Sender Gets All Own Keys (Verification) ---"
get_all_keys "$SENDER_ACCESS_TOKEN"

echo ""
echo "--- 10. Recipient Gets All Own Keys (Verification) ---"
get_all_keys "$RECIPIENT_ACCESS_TOKEN"

echo ""
echo "--- 11. Sender Fetches Recipient's Identity Key ---"
fetch_public_key "$SENDER_ACCESS_TOKEN" "$RECIPIENT_USERNAME" "identity"

echo ""
echo "--- 12. Sender Fetches Recipient's Ephemeral Key ---"
fetch_public_key "$SENDER_ACCESS_TOKEN" "$RECIPIENT_USERNAME" "ephemeral"


echo ""
echo "--- 13. Sender Gets User List ---"
get_user_list "$SENDER_ACCESS_TOKEN"


echo ""
echo "--- 14. Sender Sends Message to Recipient ---"
ENCRYPTED_MESSAGE_CONTENT="encrypted_data_for_hello_world"
SEND_MESSAGE_RESPONSE=$(send_message "$SENDER_ACCESS_TOKEN" "$RECIPIENT_USERNAME" "$ENCRYPTED_MESSAGE_CONTENT" "$RECIPIENT_EPHEMERAL_KEY_UID" "$SENDER_MESSAGE_SIGNATURE" "$SENDER_IDENTITY_KEY_UID")
SENT_MESSAGE_UID=$(echo "$SEND_MESSAGE_RESPONSE" | jq -r '.message_uid') 
echo "Message Sent (UID: '${SENT_MESSAGE_UID}'):"
echo "$SEND_MESSAGE_RESPONSE" | jq . 

if [ -z "$SENT_MESSAGE_UID" ] || [ "$SENT_MESSAGE_UID" = "null" ]; then echo "ERROR: Message send failed."; exit 1; fi


echo ""
echo "--- 15. Recipient Checks Inbox ---"
get_inbox "$RECIPIENT_ACCESS_TOKEN"

echo ""
echo "--- 16. Recipient Gets Message by UID ---"
get_message_by_id "$RECIPIENT_ACCESS_TOKEN" "$SENT_MESSAGE_UID"


echo ""
echo "--- 17. Recipient Deletes Message by UID ---"
delete_message "$RECIPIENT_ACCESS_TOKEN" "$SENT_MESSAGE_UID"


echo ""
echo "--- 18. Recipient Checks Inbox Again (should be gone) ---"
get_inbox "$RECIPIENT_ACCESS_TOKEN"


echo ""
echo "--- 19. Sender Logs Out ---"
curl $CURL_POST_COMMON_OPTS -H "Authorization: Bearer $SENDER_ACCESS_TOKEN" "${BASE_URL}/auth/logout" | jq .

echo ""
echo "--- 20. Recipient Logs Out ---"
curl $CURL_POST_COMMON_OPTS -H "Authorization: Bearer $RECIPIENT_ACCESS_TOKEN" "${BASE_URL}/auth/logout" | jq .

echo ""
echo "--- API Tests Completed ---"
