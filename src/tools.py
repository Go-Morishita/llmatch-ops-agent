# Tools

import subprocess

from langchain_core.tools import tool

from config import LAMBDA_FUNCTION_NAME

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
            cmd.append(flag)
        elif value is None or value is False:
            continue
        else:
            cmd += [flag, str(value)]
    return cmd


@tool
def run_aws_lambda_command(subcommand: str, options: dict | None = None) -> str:
    """
    Run an `aws lambda` subcommand against the target function.

    Args:
        subcommand: the aws lambda subcommand.
        options: CLI options as {name: value} without the leading "--".
            - Use True for flag options.
            - Omit "function-name" (it is injected automatically).
    """
    options = {key.lstrip("-"): value for key, value in (options or {}).items()}
    options.pop("function-name", None)
    if subcommand not in _NO_FUNCTION_NAME:
        options["function-name"] = LAMBDA_FUNCTION_NAME
    cmd = _build_command(subcommand, options)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"[aws lambda {subcommand} failed] {result.stderr.strip()}"
    return result.stdout.strip() or "(empty response)"


TOOLS = [run_aws_lambda_command]
