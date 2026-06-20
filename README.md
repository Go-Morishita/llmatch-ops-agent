# llmatch-ops-agent

サーバーログ（CloudWatch）を監視し、ローカル Qwen で分析する最小構成の LangGraph エージェント。

## 構成

```
fetch_logs --> analyze_logs --> report
 sam logs       qwen3:1.7b       標準出力
```

- ログ取得: `sam logs --stack-name llmatch-lambda-api --name WaitFunction`
- 分析モデル: ollama 経由のローカル `qwen3:1.7b`（`langchain-ollama`）

## ディレクトリ構成

```
src/         エージェント本体（agent.py / config.py / tools.py）
scripts/     手動運用ヘルパー（call-api / get-lambda-config / update-lambda-timeout）
benchmarks/  ベンチマーク実験（scenario ごとに1ファイル: timeout_repair.py ...）
results/     ベンチマーク出力（gitignore 対象）
```

## セットアップ

```bash
# 1. 仮想環境（Python 3.12）
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 2. モデル取得 & ollama 起動
ollama pull qwen3:1.7b
ollama serve   # 別ターミナル、または常駐
```

AWS 認証情報（`sam logs` 用）が設定済みであること。

## 実行

```bash
.venv/bin/python src/agent.py --model qwen3:1.7b
```

ベンチマーク（モデル別の自律修復能力を計測）:

```bash
scripts/run-benchmark.sh   # qwen3:1.7b を 3 回（プロジェクト直下から実行）
```

モデルや回数を変えるときは直接呼ぶ（`--model` / `--runs` は必須）:

```bash
.venv/bin/python benchmarks/timeout_repair.py --model qwen3:14b --runs 5
```

出力は `results/timeout_repair-<model>-<run-id>/` に `summary.csv` と
各 run のトランスクリプトとして保存される。

## 設定変更

設定はすべて [config.py](src/config.py) に集約:

- `STACK_NAME` / `FUNCTION_NAME` — 監視対象の Lambda
- `START_TIME` — `sam logs -s` に渡す時間範囲
- `SYSTEM_PROMPT` — 分析時のシステムプロンプト

モデルは config ではなく実行時の `--model` 引数で指定する（必須）。
