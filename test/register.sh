#!/bin/bash

BASE_URL="http://localhost:5000"

echo "Registering Alice..."
curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "alicepass"}' | jq

echo "Registering Bob..."
curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username": "bob", "password": "bobpass"}' | jq
