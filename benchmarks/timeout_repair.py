#!/usr/bin/env python
"""
Benchmark whether the agent autonomously fixes a Lambda timeout.

Each run: reset the timeout to BASELINE -> trigger a timeout -> run the agent
as an independent subprocess -> check if the timeout changed. Success is judged
purely from AWS (timeout before vs. after), never by parsing the agent's stdout.
Output goes to results/<run-id>/ (summary.csv + one transcript per run).

Run: .venv/bin/python benchmarks/timeout_repair.py --model qwen3:1.7b --runs 5
"""

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import LAMBDA_FUNCTION_NAME

BASELINE_TIMEOUT = 3
WAIT_TIME = 10
PROPAGATE_SLEEP = 30
ISOLATION_BUFFER = 60

AGENT = ROOT / "src" / "agent.py"
CALL_API = ROOT / "scripts" / "call-api.sh"
BENCHMARK = Path(__file__).stem


def get_timeout() -> str:
    out = subprocess.run(
        ["aws", "lambda", "get-function-configuration", "--function-name", LAMBDA_FUNCTION_NAME, "--query", "Timeout", "--output", "text"],
        capture_output=True, text=True,
    )
    return out.stdout.strip()


def set_timeout(seconds: int) -> None:
    subprocess.run(
        ["aws", "lambda", "update-function-configuration", "--function-name", LAMBDA_FUNCTION_NAME, "--timeout", str(seconds), "--query", "Timeout", "--output", "text"],
        capture_output=True, text=True,
    )


def trigger_timeout() -> None:
    subprocess.run([str(CALL_API), str(WAIT_TIME)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_agent(transcript: Path, model: str) -> None:
    with open(transcript, "w") as f:
        f.write(f"# model={model} ts={datetime.now(timezone.utc):%FT%TZ}\n")
        f.write("=" * 60 + "\n")
        f.flush()
        subprocess.run([sys.executable, str(AGENT), "--model", model], stdout=f, stderr=subprocess.STDOUT)


def main(model: str, runs: int) -> None:
    model_safe = model.replace(":", "_").replace("/", "_")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "results" / f"{BENCHMARK}-{model_safe}-{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = out_dir / "summary.csv"

    with open(summary, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["run", "timeout_before", "timeout_after", "changed", "transcript"])

        for i in range(1, runs + 1):
            set_timeout(BASELINE_TIMEOUT)
            before = get_timeout()

            time.sleep(ISOLATION_BUFFER)
            trigger_timeout()
            time.sleep(PROPAGATE_SLEEP)

            transcript = out_dir / f"run-{i}.log"
            run_agent(transcript, model)

            after = get_timeout()
            changed = "yes" if before != after else "no"

            writer.writerow([i, before, after, changed, transcript.name])
            f.flush()

    set_timeout(BASELINE_TIMEOUT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--model", required=True, help="ollama model to benchmark")
    parser.add_argument("--runs", required=True, type=int, help="number of iterations")
    args = parser.parse_args()
    main(args.model, args.runs)
