#!/bin/bash
# Base URL
BASE_URL="http://127.0.0.1:5000"

# User and dummy public key
USERNAME="alice"
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCsuZSJB5ijTaUyCFtXe6nsxrO55/D+OgzBs3/u0syCxcSRsg8i/LVafnCt2jf5EXfb/xkyLFfeQY8S7ZtO/AGqXgwg4c9SxIVr4HJWW2ntITd571x+k5kmzEs7qYQgOy0ycJsuiG39DETSEfr5qP2J8pd4tNwjo6G+8xFnEcCxhQIDAQAB-----END PUBLIC KEY-----"

echo "Registering public key for $USERNAME..."

curl -s -X POST "$BASE_URL/keys/register" -H "Content-Type: application/json" -d {"username": "$USERNAME","public_key": "$PUBLIC_KEY"}

echo -e "Done."