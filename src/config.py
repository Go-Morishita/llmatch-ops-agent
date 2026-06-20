# ============ Monitoring target ============

import os

STACK_NAME = "llmatch-lambda-api"
FUNCTION_NAME = "WaitFunction"
LAMBDA_FUNCTION_NAME = "llmatch-lambda-api-WaitFunction-eNb660N8KVQB"
START_TIME = "1 minute ago"

# ============ Model ============

# Overridable via the MODEL_NAME env var so the benchmark can compare model
# sizes (e.g. qwen3:1.7b vs qwen3:8b) without editing this file.
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3:1.7b")

# Max number of tool executions before the agent is forced to report.
# Prevents the model from looping indefinitely on failed tool calls.
MAX_TOOL_CALLS = 5

# ============ Prompt ============

SYSTEM_PROMPT = """
    You are an operations engineer monitoring server logs.

    You have a single tool:
    - run_aws_lambda(subcommand, options): run any `aws lambda` subcommand.
      Choose the right subcommand and options for the situation.
      The target function name is added automatically, so do NOT include
      "function-name" in options.
                """
