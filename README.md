# search-engine

BM25 + Vector Hybrid Search + RAG (Retrieval-Augmented Generation) REST API.

Combines SQLite FTS5 keyword search with [multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) vector search via RRF (Reciprocal Rank Fusion), and provides natural language Q&A through Ollama integration. Can also be called directly from Claude Code as an MCP server.

BM25 + ベクトル ハイブリッド検索 + RAG（Retrieval-Augmented Generation）REST API。

SQLite FTS5 によるキーワード検索と [multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) によるベクトル検索を RRF（Reciprocal Rank Fusion）で統合し、Ollama 連携で自然言語 Q&A を提供する。MCP サーバーとして Claude Code から直接呼び出すことも可能。

---

## Architecture / アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│  Client (curl / Claude Code MCP / Browser)              │
└──────────────┬──────────────────────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────────────────────┐
│  FastAPI (server.py)                                    │
│  POST /index   GET /search   POST /ask   GET /metrics   │
└──┬────────────┬────────────────────┬────────────────────┘
   │            │                    │
   ▼            ▼                    ▼
ingest.py    index.py            rag.py
              │  ├─ FTS5 (BM25)   │  ├─ ask()
              │  ├─ vector_store  │  └─ OllamaClient
              │  └─ hybrid (RRF)  │
              ▼                   ▼
          embedder.py         llm.py
          ├─ RemoteEmbedder ──▶ embedding-service:9092 (e5-base dim=768)
          └─ Embedder (fallback: ST / hash)

Storage: SQLite (FTS5 + BLOB vectors) / Qdrant (optional)
```

---

## Features / 実装済み機能

| Phase | Feature / 機能 | Implementation / 実装 |
| ----- | -------------- | --------------------- |
| 1 | BM25 keyword search (FTS5) / BM25 キーワード検索 | `index.py`, `query.py` |
| 2 | Vector search + RRF hybrid / ベクトル検索 + RRF ハイブリッド | `embedder.py`, `hybrid.py` |
| 3 | REST API server / REST API サーバー | `server.py` (FastAPI) |
| 4 | RAG — `/ask` + Ollama / `/ask` エンドポイント + Ollama 連携 | `rag.py`, `llm.py` |
| 5 | Qdrant backend + migration / Qdrant バックエンド + 移行スクリプト | `vector_store.py`, `scripts/migrate_to_qdrant.py` |
| 6 | RemoteEmbedder (e5-base) | `embedder.py` |
| 7 | MCP server (Claude Code) / MCP サーバー | `mcp_server.py` |
| 8 | Prometheus metrics / Prometheus メトリクス `/metrics` | `metrics.py` |

---

## Quick Start / クイックスタート

```bash
pip install -r requirements.txt

# Keyword index only / キーワードのみ
python3 -m searchengine.cli index ./sample_docs --db search.db

# With vector index / ベクトル索引も同時構築
EMBEDDING_URL=http://<embedding-host>:9092 \
  python3 -m searchengine.cli index ./sample_docs --db search.db --vector

# Start server / サーバー起動
cp .env.example .env
uvicorn searchengine.server:app --reload --port 8000
```

---

## API Reference / API リファレンス

All endpoints require `X-API-Key` header (skipped if `API_KEY` unset).
全エンドポイントは `X-API-Key` ヘッダーで認証（`API_KEY` 未設定時はスキップ）。

### `POST /index` — Index documents / ドキュメントをインデックス

```bash
curl -X POST http://localhost:8000/index \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/docs", "vector": true}'
```

### `GET /search` — Search / 検索

```bash
curl "http://localhost:8000/search?q=RAG+search&mode=hybrid&n=5" \
  -H "X-API-Key: $API_KEY"
```

| Parameter / パラメータ | Type / 型 | Default | Description / 説明 |
| ---------------------- | --------- | ------- | ------------------ |
| `q` | string | required / 必須 | Search query / 検索クエリ |
| `mode` | keyword\|vector\|hybrid | `keyword` | Search mode / 検索モード |
| `n` | int (1-100) | `10` | Result count / 取得件数 |

### `POST /ask` — RAG answer generation / RAG 回答生成

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RRF?", "mode": "hybrid", "top_k": 5}'
```

### `GET /metrics` — Prometheus metrics / Prometheus メトリクス

No auth required. Returns `search_requests_total`, `search_latency_seconds`, etc.
認証不要。`search_requests_total`、`search_latency_seconds` などを返す。

---

## Environment Variables / 環境変数

| Variable / 変数 | Default / デフォルト | Description / 説明 |
| --------------- | -------------------- | ------------------ |
| `SEARCH_DB` | `search.db` | SQLite DB path / SQLite DB パス |
| `API_KEY` | (unset = skip / 未設定=スキップ) | Auth key / 認証キー |
| `ALLOWED_INDEX_DIRS` | (required / 必須) | Allowed dirs for `/index` / `/index` 許可ディレクトリ |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model for RAG |
| `EMBEDDING_URL` | (unset = local fallback) | RemoteEmbedder endpoint |
| `QDRANT_URL` | (unset = SQLite) | Qdrant server URL |

---

## MCP Server / MCP サーバー（Claude Code 連携）

```json
{
  "mcpServers": {
    "search-engine": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "searchengine.mcp_server"],
      "cwd": "/path/to/search-engine",
      "env": {
        "SEARCH_DB": "/path/to/search.db",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

---

## Tests / テスト

```bash
python3 -m pytest tests/ -q
# 159 passed, 3 skipped
```

| Test file / テストファイル | Target / 対象 | Tests |
| -------------------------- | ------------- | ----- |
| `test_search.py` | FTS5 / BM25 / query parser | 34 |
| `test_server.py` | FastAPI endpoints | 47 |
| `test_rag.py` | RAG pipeline + /ask | 10 |
| `test_embedder.py` | Embedder / RemoteEmbedder | 16 |
| `test_mcp_server.py` | MCP server | 11 |
