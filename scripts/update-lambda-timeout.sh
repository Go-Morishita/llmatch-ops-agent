#!/usr/bin/env bash

FUNCTION_NAME="llmatch-lambda-api-WaitFunction-eNb660N8KVQB"
TIMEOUT="$1"

aws lambda update-function-configuration \
  --function-name "${FUNCTION_NAME}" \
  --timeout "${TIMEOUT}" \
  --query '{Function:FunctionName, Timeout:Timeout}' \
  --output table
