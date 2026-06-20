# ============ Target ============

STACK_NAME = "llmatch-lambda-api"
FUNCTION_NAME = "WaitFunction"
LAMBDA_FUNCTION_NAME = "llmatch-lambda-api-WaitFunction-eNb660N8KVQB"
START_TIME = "1 minute ago"

# ============ Settings ============

MAX_TOOL_CALLS = 5
SYSTEM_PROMPT = (
    "You are an operations engineer responsible for the server. "
    "Investigate the logs, and if something is wrong, use your tools to resolve it."
)
