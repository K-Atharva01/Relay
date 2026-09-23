#!/bin/bash

BASE_URL="http://100.102.195.25:5000"
USERNAME="userB"
PASSWORD="userBpassword"
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt5HofbJjPDaDrI3uJ015sAOEtwgzC/iZGAZM9z/GJT458+1+YeS5YTzMaFoUfBn28jRBqV/V7xe0v7rzQ/dyM4jyDdqq2VXVoF/UZKdbsRNwoZ9+TQ3c3cVCWmHnmk/v3lB+rGoqMAKKnGwdNvr5OC/jJJ9wZJIBjA7t+NVDQpLXD/FdFbVLw8HPz60BynMjDBNl0fGLWdOVUnFh63kZNGjYW5mo4Uaf3OKA1/2yHjTL6rYIvITb0zAtg39KyM94s0i4VJKRSztbE1P4ZvDY+yyLtrVb9cx8/QtiquTHGih4CaWFf9zLJY+XMOOmYeH44q/clSzcK/atAzWChhcBywIDAQAB-----END PUBLIC KEY-----"

echo "✅ Registering user..."
curl -s -X POST "$BASE_URL/auth/register" -H "Content-Type: application/json" -d "{\"username\":\"$USERNAME\", \"password\":\"$PASSWORD\", \"public_key\":\"$PUBLIC_KEY\"}"

echo -e "\n\n🔐 Logging in..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" -d "{\"username\":\"$USERNAME\", \"password\":\"$PASSWORD\"}" | jq -r .access_token)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    exit 1
else
    echo "✅ Login successful"
    echo "JWT Token: $TOKEN"
fi

echo -e "\n🔒 Accessing protected route (/me)..."
curl -s -X GET "$BASE_URL/keys/$USERNAME" -H "Authorization: Bearer $TOKEN"

echo -e "\n\n🚪 Logging out..."
curl -s -X POST "$BASE_URL/auth/logout" -H "Authorization: Bearer $TOKEN"

echo -e "\n\n🔁 Trying to access protected route after logout..."
curl -s -X GET "$BASE_URL/auth/$USERNAME" -H "Authorization: Bearer $TOKEN"
