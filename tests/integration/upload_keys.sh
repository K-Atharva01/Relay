#!/bin/bash

BASE_URL="http://192.168.0.200:5000"

ALICE_TOKEN=$(cat alice.token)
BOB_TOKEN=$(cat bob.token)

# Adding a key requires the account password as well as the token.
read -rsp "Alice's password: " ALICE_PASSWORD; echo
read -rsp "Bob's password: " BOB_PASSWORD; echo

ALICE_KEY=$'-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0fyhhOMqWCTRFbs8K3wh\neglhMWZ8lgmL3PsrwVjCAaNED6ahxIjXJZUiHO1wHCIdFwnhd6SZwDP5q71fx997\n1iw8mnlnPRmdvEW/zjI1TURHoxpxah6gpe3M/Hv8Vaw05zPSvUj2QF4MgErmDAnq\nlC93XAvPiP2H2ft7ddfYVfPWLGXJ7VoegqYY1DCpCF0DQYDXVpRgm23zkfKNqHZd\nCKLoZS6kC52zUQkhEl4z2Osep9IH50t3PdpfOpZz8ZGFI/w53iBKPNGLcDRfxsqo\nP0Ofh6WMBQ1pixHft9Nz1A5YhhZ2bsl500OBnoJgQWm5He/gvK28mFWRY8zvwOVK\n5QIDAQAB\n-----END PUBLIC KEY-----'
# A valid RSA-2048 public key. Public keys are not secret; no private key
# is stored in the repository. Both users upload the same test key.
BOB_KEY=$ALICE_KEY

# The password is passed to jq through the environment, not as an argument,
# so it does not show up in the process list.
upload_key() {
    local token=$1 key=$2 password=$3
    PASSWORD="$password" jq -n --arg key "$key" '{public_key: $key, password: env.PASSWORD}' |
    curl -s -X POST "$BASE_URL/keys/addKey" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d @- | jq
}

echo "Uploading Alice's public key..."
upload_key "$ALICE_TOKEN" "$ALICE_KEY" "$ALICE_PASSWORD"

echo "Uploading Bob's public key..."
upload_key "$BOB_TOKEN" "$BOB_KEY" "$BOB_PASSWORD"
