#!/bin/bash

# Base URL for your Flask API
BASE_URL="http://192.168.0.200:5000"

# Common curl options for POST and GET requests
# -s: Silent mode (removes progress meter)
# -X POST/GET: Specifies the HTTP method
CURL_POST_COMMON_OPTS="-s -X POST"
CURL_GET_COMMON_OPTS="-s -X GET"

# Temporary files for storing shared state between tests
# We'll use /tmp for general temporary files, which are usually cleaned up on reboot.
SENDER_TOKEN_FILE="/tmp/_sender_token.tmp"
RECIPIENT_TOKEN_FILE="/tmp/_recipient_token.tmp"
SENDER_IDENTITY_KEY_UID_FILE="/tmp/_sender_identity_key_uid.tmp"
SENDER_EPHEMERAL_KEY_UID_FILE="/tmp/_sender_ephemeral_key_uid.tmp"
RECIPIENT_IDENTITY_KEY_UID_FILE="/tmp/_recipient_identity_key_uid.tmp"
RECIPIENT_EPHEMERAL_KEY_UID_FILE="/tmp/_recipient_ephemeral_key_uid.tmp"
LAST_SENT_MESSAGE_UID_FILE="/tmp/_last_sent_message_uid.tmp"

# Placeholder public keys and signatures (replace with real ones if needed for actual crypto tests)
SENDER_IDENTITY_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nSENDER_IDENTITY_PUB_KEY_PLACEHOLDER_1\n-----END PUBLIC KEY-----"
SENDER_EPHEMERAL_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nSENDER_EPHEMERAL_PUB_KEY_PLACEHOLDER_1\n-----END PUBLIC KEY-----"
SENDER_MESSAGE_SIGNATURE="SENDER_SIGNATURE_FOR_MESSAGE_PLACEHOLDER"

RECIPIENT_IDENTITY_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nRECIPIENT_IDENTITY_PUB_KEY_PLACEHOLDER_2\n-----END PUBLIC KEY-----"
RECIPIENT_EPHEMERAL_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\nRECIPIENT_EPHEMERAL_PUB_KEY_PLACEHOLDER_2\n-----END PUBLIC KEY-----"

# --- Helper Functions (used across multiple scripts) ---

# Function to read a value from a temporary file, with an optional error message
read_from_tmp() {
    local file=$1
    local error_msg=$2
    if [[ ! -f "$file" ]]; then
        echo "Error: $error_msg (file not found: $file)" >&2
        exit 1
    fi
    cat "$file"
}

# Function to write a value to a temporary file
write_to_tmp() {
    local file=$1
    local value=$2
    echo "$value" > "$file"
}

# Function to clean up all temporary files
cleanup_tmp_files() {
    echo "Cleaning up temporary files..."
    rm -f \
        "$SENDER_TOKEN_FILE" \
        "$RECIPIENT_TOKEN_FILE" \
        "$SENDER_IDENTITY_KEY_UID_FILE" \
        "$SENDER_EPHEMERAL_KEY_UID_FILE" \
        "$RECIPIENT_IDENTITY_KEY_UID_FILE" \
        "$RECIPIENT_EPHEMERAL_KEY_UID_FILE" \
        "$LAST_SENT_MESSAGE_UID_FILE"
}
