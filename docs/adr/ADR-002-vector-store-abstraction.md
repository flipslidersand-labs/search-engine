# ADR-002: ベクトルストアを共通インターフェースで抽象化し、SQLite と Qdrant を切り替えられるようにする

**ステータス:** Draft  
**決定日:** 未確認（遡及記録: 2026-10-28）  
**review_by:** 2026-11-17

> 雛形: [ADR-000-public-template](https://github.com/flipslidersand-labs/repo-compass/blob/master/docs/adr/ADR-000-public-template.md)。遡及して書いた記録で、当時の比較経緯は推定していない。

---

## 課題

小さな規模では SQLite だけで動かしたいが、規模が増えたときには Qdrant に移したい。

## 決定

ベクトルストアの操作（`upsert` / `delete_doc` / `search` / `close`）を `VectorStoreProtocol` として定め、
`SqliteVectorStore` と `QdrantVectorStore` の 2 つで実装する。Qdrant への移行用に `scripts/migrate_to_qdrant.py` を持つ。

## 理由

- 呼び出し側が、ストアの種類を意識しないで済む。
- **却下した代替案:** どちらか一方に固定する。比較した記録はない（当時の検討は未確認）。

## 影響

- 2 つの実装の挙動をそろえるテストが必要になる。
- 移行は、移行スクリプトを実行する手順であり、無停止であることは、この記録では確認していない。

## 再検討条件

どちらかのストアしか使われなくなったとき。

## 関連

- `searchengine/vector_store.py`、`scripts/migrate_to_qdrant.py`
