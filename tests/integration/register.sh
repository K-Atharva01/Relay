#!/bin/bash

BASE_URL="http://192.168.0.200:5000"

echo "Registering Alice..."
curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "alicepass1234", "name":"Alice", "phone":"1234567890", "email":"alice@email.com"}' | jq

echo "Registering Bob..."
curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username": "bob", "password": "bobpass12345", "name":"bob", "phone":"1234567891", "email":"bob@email.com"}' | jq
