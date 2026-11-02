# 設計判断（ADR）/ Design decisions

遡及して整理した Draft。当時の比較経緯は推定していない。雛形は repo-compass の ADR-025（public リポの ADR の基準）に従う。

| ADR | EN | 題 | 状態 |
| --- | --- | --- | --- |
| [ADR-001](ADR-001-rrf-for-hybrid-search.md) | RRF for hybrid search | 統合に RRF（k=60）を使う | Draft |
| [ADR-002](ADR-002-vector-store-abstraction.md) | Vector store abstraction | ベクトルストアを抽象化し、SQLite と Qdrant を切り替えられるようにする | Draft |
| [ADR-003](ADR-003-allowed-index-dirs-required.md) | `ALLOWED_INDEX_DIRS` required | `/index` は許可ディレクトリを必須にする | Draft |
