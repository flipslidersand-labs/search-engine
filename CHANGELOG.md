# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). No versions have been tagged yet, so everything is under `Unreleased`; entries are derived from merged PRs.
バージョン未採番のため、すべて `Unreleased`。マージ済み PR の題名と番号から起こしている。

## [Unreleased]

### Added
- Discord notifier for index completion/errors ([#109](../../pull/109))
- Contextual prefix (Contextual Retrieval) generation and ingest/index integration ([#86](../../pull/86), [#87](../../pull/87)); Pass@k evaluation ([#88](../../pull/88))
- Guard that keeps chunks within the e5 512-token limit when building the vector index ([#96](../../pull/96))
- `nugget` search mode ([#75](../../pull/75))
- MCP server (search / ask / index / stats) ([#62](../../pull/62)); RemoteEmbedder batch API ([#67](../../pull/67)) and fallback chain with retry ([#61](../../pull/61))
- Prometheus metrics and `/metrics` ([#60](../../pull/60))
- Qdrant vector store, `create_vector_store` factory and SQLite→Qdrant migration script ([#54](../../pull/54), [#55](../../pull/55)); `VectorStoreProtocol` ([#50](../../pull/50))
- `/index` continues past a single-file failure ([#114](../../pull/114))
- `.env.example` with required `ALLOWED_INDEX_DIRS` ([#154](../../pull/154)); optional dependencies declared ([#149](../../pull/149)); `requirements.lock.txt` ([#94](../../pull/94), [#116](../../pull/116))
- CI: gitleaks secrets scan ([#98](../../pull/98)), pip-audit on the lock file ([#158](../../pull/158)), ruff lint gate ([#81](../../pull/81)), reusable python-test workflow ([#80](../../pull/80))
- ADRs for three design decisions ([#106](../../pull/106)); README detail ([#63](../../pull/63), [#64](../../pull/64))

### Changed
- `/ask` uses `LLMError` instead of exposing httpx; function-local imports moved to module level ([#163](../../pull/163))
- Index connections are closed via `with` in server and MCP paths ([#162](../../pull/162))
- server/cli build the embedder with `create_embedder()` and honor `EMBEDDING_URL` ([#157](../../pull/157))
- `QdrantVectorStore` point IDs are deterministic (uuid5). **Existing Qdrant collections must be rebuilt.** ([#160](../../pull/160))
- Missing `API_KEY` now fails closed; key comparison is constant-time. Set `ALLOW_NO_AUTH=1` for local development only ([#146](../../pull/146))
- Container runs as non-root with a read-only root filesystem ([#150](../../pull/150))
- Dockerfile and CI install from `requirements.lock.txt` ([#116](../../pull/116)); reusable workflow pinned by SHA ([#142](../../pull/142), [#155](../../pull/155))
- `track_*` metrics helpers consolidated ([#99](../../pull/99)); `ImportError` fallback removed from `metrics.py` ([#161](../../pull/161))
- Healthcheck uses python urllib instead of curl ([#71](../../pull/71))

### Fixed
- Operator-only / leading / trailing operator queries no longer raise FTS5 syntax errors; other DB errors are not swallowed ([#153](../../pull/153))
- `top_k` range validation; no LLM call when there are zero sources ([#152](../../pull/152))
- `nugget` mode extracts from chunk text ([#151](../../pull/151)); BM25 IDF uses document frequency ([#156](../../pull/156))
- Web UI escapes error messages ([#145](../../pull/145)); symlinks pointing outside allowed dirs are not indexed ([#144](../../pull/144))
- `add_document` rolls back on failure ([#112](../../pull/112)); vector search ignores vectors of a different dimension ([#111](../../pull/111)); `truncate_to_tokens` is single-pass ([#101](../../pull/101))
- ruff pinned to fix runner-dependent UP017 failure ([#100](../../pull/100))
- Question-ending particles stripped from FTS queries ([#70](../../pull/70)); MCP handlers follow the `mcp>=2.0` runtime contract ([#68](../../pull/68))

### Security
- MCP `index` validates `ALLOWED_INDEX_DIRS` and no longer accepts a `db` argument ([#143](../../pull/143)); HTTP API no longer accepts an arbitrary `db` path ([#115](../../pull/115))
- `/schema/*` auth bypass, arbitrary file read and `ollama_url` SSRF fixed ([#93](../../pull/93))
- API-key authentication and `/index` path-traversal protection ([#58](../../pull/58), [#57](../../pull/57))
- Internal LAN IP removed from `deploy.sh` messages ([#108](../../pull/108))
- Vulnerable locked packages updated: certifi, opentelemetry-api, pyjwt ([#159](../../pull/159))
