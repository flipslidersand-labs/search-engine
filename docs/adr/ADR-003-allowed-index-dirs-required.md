# ADR-003: `/index` は、許可ディレクトリ（`ALLOWED_INDEX_DIRS`）を必須にする

**ステータス:** Draft  
**決定日:** 未確認（遡及記録: 2026-10-28）  
**review_by:** 2026-11-17

> 雛形: [ADR-000-public-template](https://github.com/flipslidersand-labs/repo-compass/blob/master/docs/adr/ADR-000-public-template.md)。遡及して書いた記録で、当時の比較経緯は推定していない。

---

## 課題

`/index` はサーバー上のパスを受け取って文書を読み込む。許可を設けないと、任意のディレクトリを読ませられる（パストラバーサル）。

## 決定

環境変数 `ALLOWED_INDEX_DIRS` を必須にする。未設定の場合、`/index` は 403 を返し、メッセージで `ALLOWED_INDEX_DIRS` を示す。
許可ディレクトリの外のパスも拒否する。

## 理由

- 既定を「拒否」にすると、設定のし忘れが、情報の漏えいではなく、エラーになる。
- **却下した代替案:** 既定で任意のディレクトリを許可する。比較した記録はない（当時の検討は未確認）。

## 影響

- 利用者は、起動前に許可ディレクトリを設定する必要がある。
- 拒否の挙動は `tests/test_server.py` のテスト（許可なし・許可外）で確認している。

## 再検討条件

認証・認可の仕組みを足すとき。

## 関連

- `tests/test_server.py`（#32）、README の環境変数の表
