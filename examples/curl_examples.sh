#!/bin/bash
# SimpleLogs curl examples

API_KEY="YOUR_API_KEY"
BASE_URL="http://localhost"

# Simple log
curl -X POST "$BASE_URL/api/v1/ingest" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"level": "info", "message": "User logged in"}'

# Log with metadata
curl -X POST "$BASE_URL/api/v1/ingest" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "error",
    "message": "Payment failed",
    "source": "payment-service",
    "metadata": {
      "user_id": 123,
      "order_id": 456,
      "amount": 99.99,
      "error_code": "CARD_DECLINED"
    }
  }'

# Batch logging (up to 1000 logs)
curl -X POST "$BASE_URL/api/v1/ingest/batch" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"level": "info", "message": "Request received"},
      {"level": "debug", "message": "Processing data", "metadata": {"items": 5}},
      {"level": "info", "message": "Request completed"}
    ]
  }'
