#!/usr/bin/env bash

FUNCTION_NAME="llmatch-lambda-api-WaitFunction-eNb660N8KVQB"

aws lambda get-function-configuration \
  --function-name "${FUNCTION_NAME}" \
  --query '{Function:FunctionName, Timeout:Timeout}' \
  --output table
