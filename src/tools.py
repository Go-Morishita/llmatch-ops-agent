# Tool definitions used by the agent.

import subprocess

from langchain_core.tools import tool

from config import LAMBDA_FUNCTION_NAME

# Subcommands that do NOT accept --function-name, so we must not inject it.
_NO_FUNCTION_NAME = {
    "list-functions",
    "list-layers",
    "list-layer-versions",
    "list-event-source-mappings",
    "get-account-settings",
}


def _build_command(subcommand: str, options: dict | None) -> list[str]:
    """Build an `aws lambda <subcommand> --opt val ...` argument vector."""
    cmd = ["aws", "lambda", subcommand]
    for key, value in (options or {}).items():
        flag = f"--{key}"
        if value is True:
            # store_true style option, e.g. --dry-run
            cmd.append(flag)
        elif value is None or value is False:
            # skip unset / disabled options
            continue
        else:
            cmd += [flag, str(value)]
    return cmd


@tool
def run_aws_lambda(subcommand: str, options: dict | None = None) -> str:
    """Run an `aws lambda` subcommand.

    Use this for any AWS Lambda operation.

    The target function name is injected automatically — do NOT provide
    "function-name" yourself.

    Args:
        subcommand: the aws lambda subcommand, e.g. "get-function-configuration",
            "update-function-configuration", "invoke", "list-functions".
        options: CLI options as a dict, with the option name (without the leading
            "--") as the key. Example: {"timeout": 30}. Pass True for flag-style
            options (e.g. {"dry-run": True}). Omit "function-name".
    """
    options = dict(options or {})
    if subcommand not in _NO_FUNCTION_NAME:
        # Provide the function name from config instead of trusting the model.
        options["function-name"] = LAMBDA_FUNCTION_NAME
    cmd = _build_command(subcommand, options)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"[aws lambda {subcommand} failed] {result.stderr.strip()}"
    return result.stdout.strip() or "(empty response)"


TOOLS = [run_aws_lambda]
