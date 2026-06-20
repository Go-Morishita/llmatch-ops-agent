#!/usr/bin/env bash
#
# Benchmark loop for the ops agent — runs a SINGLE model per invocation.
# The model name is passed as an argument so the exact same code runs for
# every model; compare sizes by invoking the script once per model.
#
# Each iteration:
#   1. reset the Lambda timeout to a low BASELINE (experiment initialization)
#   2. call the API with WAIT_TIME (> BASELINE) to deliberately cause a timeout
#   3. wait for logs to propagate to CloudWatch
#   4. run the agent with the given model, saving its full output to a log file
#   5. record whether the agent changed the timeout (i.e. fixed the problem)
#
# Results are written under logs/<model>-<run-id>/ :
#   run-N.log     full agent output for iteration N
#   summary.csv   one row per iteration
#
# Usage:
#   scripts/benchmark.sh                       # default model (qwen3:1.7b)
#   scripts/benchmark.sh qwen3:8b              # benchmark one model
#   RUNS=10 scripts/benchmark.sh qwen3:14b     # 10 runs of one model

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
FUNCTION_NAME="llmatch-lambda-api-WaitFunction-eNb660N8KVQB"

# Model to benchmark: first argument, else $MODEL_NAME, else the default.
MODEL="${1:-${MODEL_NAME:-qwen3:1.7b}}"

# --- tunables (override via env) ---
BASELINE_TIMEOUT="${BASELINE_TIMEOUT:-3}"   # low timeout that triggers a timeout
WAIT_TIME="${WAIT_TIME:-10}"                # API sleep seconds, must exceed BASELINE
RUNS="${RUNS:-5}"                           # number of iterations
PROPAGATE_SLEEP="${PROPAGATE_SLEEP:-20}"    # seconds to wait for logs to appear

# Prefer the project venv python so it runs the same as `python src/agent.py`.
PYTHON="$ROOT_DIR/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python"

get_timeout() {
  aws lambda get-function-configuration --function-name "$FUNCTION_NAME" \
    --query 'Timeout' --output text
}

set_timeout() {
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \
    --timeout "$1" --query 'Timeout' --output text >/dev/null
}

# filesystem-safe model name for paths
MODEL_SAFE="${MODEL//[:\/]/_}"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT_DIR/logs/${MODEL_SAFE}-${RUN_ID}"
mkdir -p "$LOG_DIR"
SUMMARY="$LOG_DIR/summary.csv"
echo "model,run,timeout_before,timeout_after,changed,called_update,agent_log" > "$SUMMARY"

echo "Benchmark: MODEL=$MODEL RUNS=$RUNS BASELINE_TIMEOUT=$BASELINE_TIMEOUT WAIT_TIME=$WAIT_TIME"
echo "Logs: $LOG_DIR"

for i in $(seq 1 "$RUNS"); do
  echo "============================================================"
  echo "[$MODEL] Run $i/$RUNS"

  # 1. initialize / reset the experiment environment
  set_timeout "$BASELINE_TIMEOUT"
  before="$BASELINE_TIMEOUT"

  # 2. deliberately cause a timeout (the API waits longer than the timeout)
  echo "  triggering timeout (time=$WAIT_TIME, timeout=$BASELINE_TIMEOUT)..."
  "$SCRIPT_DIR/call-api.sh" "$WAIT_TIME" >/dev/null 2>&1 || true

  # 3. wait for CloudWatch logs to become visible to the agent
  sleep "$PROPAGATE_SLEEP"

  # 4. run the agent with the selected model and save its behaviour
  agent_log="$LOG_DIR/run-$i.log"
  {
    echo "# model=$MODEL run=$i timestamp=$(date -u +%FT%TZ) timeout_before=$before"
    echo "============================================================"
  } > "$agent_log"
  ( cd "$ROOT_DIR" && MODEL_NAME="$MODEL" "$PYTHON" src/agent.py ) >> "$agent_log" 2>&1 || true

  # 5. did the agent change (fix) the timeout?
  after="$(get_timeout)"
  changed="no"
  [ "$before" != "$after" ] && changed="yes"

  # did the agent even attempt the correct action?
  called_update="no"
  grep -q "subcommand': 'update-function-configuration'" "$agent_log" && called_update="yes"

  echo "$MODEL,$i,$before,$after,$changed,$called_update,run-$i.log" >> "$SUMMARY"
  echo "  before=$before after=$after changed=$changed called_update=$called_update -> $agent_log"
done

# leave the environment back at baseline
set_timeout "$BASELINE_TIMEOUT"

echo "============================================================"
echo "Done. Summary:"
cat "$SUMMARY"
