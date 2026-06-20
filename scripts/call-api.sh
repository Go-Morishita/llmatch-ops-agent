#!/usr/bin/env bash

API_URL="https://2wtmo9mdo6.execute-api.ap-northeast-1.amazonaws.com/Prod/api/"
TIME="${1:-0}"

curl -s -X POST "${API_URL}" \
  -H "Content-Type: application/json" \
  -d "{\"time\": ${TIME}}"
echo
