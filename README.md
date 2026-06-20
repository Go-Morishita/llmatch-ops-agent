# llmatch-ops-agent

サーバーログ（CloudWatch）を監視し、ローカル Qwen で分析する最小構成の LangGraph エージェント。

## 構成

```
fetch_logs --> analyze_logs --> report
 sam logs       qwen3:1.7b       標準出力
```

- ログ取得: `sam logs --stack-name llmatch-lambda-api --name WaitFunction`
- 分析モデル: ollama 経由のローカル `qwen3:1.7b`（`langchain-ollama`）

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
.venv/bin/python agent.py
```

## 設定変更

設定はすべて [config.py](config.py) に集約:

- `STACK_NAME` / `FUNCTION_NAME` — 監視対象の Lambda
- `START_TIME` — `sam logs -s` に渡す時間範囲
- `MODEL_NAME` — 利用する ollama モデル
- `SYSTEM_PROMPT` — 分析時のシステムプロンプト
