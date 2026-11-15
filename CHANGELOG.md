# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). No versions have been tagged yet, so everything is under `Unreleased`; entries are derived from merged PRs.

バージョン未採番のため、すべて `Unreleased`。マージ済み PR の題名と番号から起こしている。

## [Unreleased]

### Added
- Discord notifier for index completion/errors ([#109](https://github.com/flipslidersand-labs/search-engine/pull/109))
- Contextual prefix (Contextual Retrieval) generation and ingest/index integration ([#86](https://github.com/flipslidersand-labs/search-engine/pull/86), [#87](https://github.com/flipslidersand-labs/search-engine/pull/87)); Pass@k evaluation ([#88](https://github.com/flipslidersand-labs/search-engine/pull/88))
- Guard that keeps chunks within the e5 512-token limit when building the vector index ([#96](https://github.com/flipslidersand-labs/search-engine/pull/96))
- `nugget` search mode ([#75](https://github.com/flipslidersand-labs/search-engine/pull/75))
- MCP server (search / ask / index / stats) ([#62](https://github.com/flipslidersand-labs/search-engine/pull/62)); RemoteEmbedder batch API ([#67](https://github.com/flipslidersand-labs/search-engine/pull/67)) and fallback chain with retry ([#61](https://github.com/flipslidersand-labs/search-engine/pull/61))
- Prometheus metrics and `/metrics` ([#60](https://github.com/flipslidersand-labs/search-engine/pull/60))
- Qdrant vector store, `create_vector_store` factory and SQLite→Qdrant migration script ([#54](https://github.com/flipslidersand-labs/search-engine/pull/54), [#55](https://github.com/flipslidersand-labs/search-engine/pull/55)); `VectorStoreProtocol` ([#50](https://github.com/flipslidersand-labs/search-engine/pull/50))
- `/index` continues past a single-file failure ([#114](https://github.com/flipslidersand-labs/search-engine/pull/114))
- `.env.example` with required `ALLOWED_INDEX_DIRS` ([#154](https://github.com/flipslidersand-labs/search-engine/pull/154)); optional dependencies declared ([#149](https://github.com/flipslidersand-labs/search-engine/pull/149)); `requirements.lock.txt` ([#94](https://github.com/flipslidersand-labs/search-engine/pull/94), [#116](https://github.com/flipslidersand-labs/search-engine/pull/116))
- CI: gitleaks secrets scan ([#98](https://github.com/flipslidersand-labs/search-engine/pull/98)), pip-audit on the lock file ([#158](https://github.com/flipslidersand-labs/search-engine/pull/158)), ruff lint gate ([#81](https://github.com/flipslidersand-labs/search-engine/pull/81)), reusable python-test workflow ([#80](https://github.com/flipslidersand-labs/search-engine/pull/80))
- ADRs for three design decisions ([#106](https://github.com/flipslidersand-labs/search-engine/pull/106)); README detail ([#63](https://github.com/flipslidersand-labs/search-engine/pull/63), [#64](https://github.com/flipslidersand-labs/search-engine/pull/64))

### Changed
- `/ask` uses `LLMError` instead of exposing httpx; function-local imports moved to module level ([#163](https://github.com/flipslidersand-labs/search-engine/pull/163))
- Index connections are closed via `with` in server and MCP paths ([#162](https://github.com/flipslidersand-labs/search-engine/pull/162))
- server/cli build the embedder with `create_embedder()` and honor `EMBEDDING_URL` ([#157](https://github.com/flipslidersand-labs/search-engine/pull/157))
- `QdrantVectorStore` point IDs are deterministic (uuid5). **Existing Qdrant collections must be rebuilt.** ([#160](https://github.com/flipslidersand-labs/search-engine/pull/160))
- Missing `API_KEY` now fails closed; key comparison is constant-time. Set `ALLOW_NO_AUTH=1` for local development only ([#146](https://github.com/flipslidersand-labs/search-engine/pull/146))
- Container runs as non-root with a read-only root filesystem ([#150](https://github.com/flipslidersand-labs/search-engine/pull/150))
- Reusable workflow pinned by SHA ([#142](https://github.com/flipslidersand-labs/search-engine/pull/142), [#155](https://github.com/flipslidersand-labs/search-engine/pull/155))
- `track_*` metrics helpers consolidated ([#99](https://github.com/flipslidersand-labs/search-engine/pull/99)); `ImportError` fallback removed from `metrics.py` ([#161](https://github.com/flipslidersand-labs/search-engine/pull/161))
- Healthcheck uses python urllib instead of curl ([#71](https://github.com/flipslidersand-labs/search-engine/pull/71))

### Fixed
- Operator-only / leading / trailing operator queries no longer raise FTS5 syntax errors; other DB errors are not swallowed ([#153](https://github.com/flipslidersand-labs/search-engine/pull/153))
- `top_k` range validation; no LLM call when there are zero sources ([#152](https://github.com/flipslidersand-labs/search-engine/pull/152))
- `nugget` mode extracts from chunk text ([#151](https://github.com/flipslidersand-labs/search-engine/pull/151)); BM25 IDF uses document frequency ([#156](https://github.com/flipslidersand-labs/search-engine/pull/156))
- Web UI escapes error messages ([#145](https://github.com/flipslidersand-labs/search-engine/pull/145)); symlinks pointing outside allowed dirs are not indexed ([#144](https://github.com/flipslidersand-labs/search-engine/pull/144))
- `add_document` rolls back on failure ([#112](https://github.com/flipslidersand-labs/search-engine/pull/112)); vector search ignores vectors of a different dimension ([#111](https://github.com/flipslidersand-labs/search-engine/pull/111)); `truncate_to_tokens` is single-pass ([#101](https://github.com/flipslidersand-labs/search-engine/pull/101))
- ruff pinned to fix runner-dependent UP017 failure ([#100](https://github.com/flipslidersand-labs/search-engine/pull/100))
- Question-ending particles stripped from FTS queries ([#70](https://github.com/flipslidersand-labs/search-engine/pull/70)); MCP handlers follow the `mcp>=2.0` runtime contract ([#68](https://github.com/flipslidersand-labs/search-engine/pull/68))

### Security
- MCP `index` validates `ALLOWED_INDEX_DIRS` and no longer accepts a `db` argument ([#143](https://github.com/flipslidersand-labs/search-engine/pull/143)); HTTP API no longer accepts an arbitrary `db` path ([#115](https://github.com/flipslidersand-labs/search-engine/pull/115))
- `/schema/*` auth bypass, arbitrary file read and `ollama_url` SSRF fixed ([#93](https://github.com/flipslidersand-labs/search-engine/pull/93))
- API-key authentication and `/index` path-traversal protection ([#58](https://github.com/flipslidersand-labs/search-engine/pull/58), [#57](https://github.com/flipslidersand-labs/search-engine/pull/57))
- Internal LAN IP removed from `deploy.sh` messages ([#108](https://github.com/flipslidersand-labs/search-engine/pull/108))
- Vulnerable locked packages updated: certifi, opentelemetry-api, pyjwt ([#159](https://github.com/flipslidersand-labs/search-engine/pull/159))
