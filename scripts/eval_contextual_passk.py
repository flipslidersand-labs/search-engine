#!/usr/bin/env python3
"""Contextual prefix (#78/#82/#83) 導入前後の Pass@k 比較評価（#84）。

qa-platform（従来このRAG評価を担っていたリポ）は2026-09-14にアーカイブ済み
のため、search-engine 内に最小限の評価ツールを新規作成した。

手法:
  複数の似た構造を持つセクションから成る文書を1つ用意する（GOLD_DOC）。
  各セクションは固有名詞（システム名）を序盤で述べたあと、後半は指示語
  （「これは」「障害時は」等）で参照する構成にしている。チャンクサイズを
  小さく切ると、後半のチャンクは固有名詞を含まず「どのシステムの話か」を
  失う ── これがContextual Retrievalが解決しようとする典型的な失敗モード。

  各セクションを名指しするクエリ（GOLD_QUERIES）に対し、prefixなし
  （baseline）と prefixあり（contextual、Ollamaで生成）でFTS(BM25)検索の
  Pass@k を比較する。

  検索方式はFTS(BM25)のみを対象とする。ベクトル検索は sentence-transformers
  のインストールを要求し評価環境への依存を増やすため対象外とした
  （content列へのprefix前置はFTSにもベクトル埋め込みにも同様に効くため、
  FTSだけでも導入効果の検証としては妥当）。

使い方:
  python3 scripts/eval_contextual_passk.py             # k=3 で実行
  python3 scripts/eval_contextual_passk.py --k 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from searchengine import chunker, query, tokenizer
from searchengine.contextual import add_context
from searchengine.index import SCHEMA, Hit, _doc_id

CHUNK_SIZE = 5  # 小さく切って「固有名詞を失ったチャンク」を意図的に作る
# 注: chunker は空白区切り語数でサイズを近似するため（日本語は改行区切りの
# 行が1〜2語相当になりやすい）、実文書よりかなり小さい値になる。段落単位で
# チャンクが割れることを狙った値。

GOLD_DOCS = [
    (
        "/eval/systems.md",
        """# 社内システム概要

## Falcon

Falconは在庫管理システムである。倉庫の入出庫をリアルタイムに追跡し、
複数拠点の在庫状況を一元管理する。

これは2019年に導入され、現在も主力システムとして稼働している。
障害時のフェイルオーバーは自動で行われ、運用チームの負荷を大きく下げている。
定期メンテナンスは毎週日曜の深夜に実施される。

## Osprey

Ospreyは請求書発行システムである。月次で顧客への請求書を自動生成し、
支払い状況も追跡する。

これは2021年に導入され、経理部門の手作業を大幅に削減した。
障害時のフェイルオーバーは自動で行われ、運用チームの負荷を大きく下げている。
定期メンテナンスは毎週日曜の深夜に実施される。

## Kestrel

Kestrelは社内チャットシステムである。全社員が日常的に利用しており、
ファイル共有機能も備える。

これは2020年に導入され、以降社内コミュニケーションの中心となっている。
障害時のフェイルオーバーは自動で行われ、運用チームの負荷を大きく下げている。
定期メンテナンスは毎週日曜の深夜に実施される。
""",
    ),
]

GOLD_QUERIES = [
    ("Falcon フェイルオーバー", "/eval/systems.md"),
    ("Osprey フェイルオーバー", "/eval/systems.md"),
    ("Kestrel フェイルオーバー", "/eval/systems.md"),
    ("在庫管理システムのメンテナンス", "/eval/systems.md"),
    ("請求書発行システムのメンテナンス", "/eval/systems.md"),
    ("社内チャットシステムのメンテナンス", "/eval/systems.md"),
]


def _build_raw_index(use_context: bool) -> sqlite3.Connection:
    """Index.add_document を経由せず、明示的に小さい chunk size で構築する。"""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    for path, text in GOLD_DOCS:
        doc_id = _doc_id(path)
        chunks = chunker.chunk_text(text, size=CHUNK_SIZE, overlap=0)
        search_chunks = add_context(text, chunks) if use_context else chunks
        for ch, search_ch in zip(chunks, search_chunks):
            conn.execute(
                "INSERT INTO chunks_fts (content, original, doc_id, chunk_index)"
                " VALUES (?, ?, ?, ?)",
                (tokenizer.tokenized_text(search_ch.text), ch.text, doc_id, ch.index),
            )
        conn.execute(
            "INSERT INTO documents (doc_id, path, doc_type, mtime, hash) VALUES (?, ?, ?, ?, ?)",
            (doc_id, path, "eval", 0.0, "eval"),
        )
    conn.commit()
    return conn


def _search(conn: sqlite3.Connection, fts_query: str, limit: int) -> list[Hit]:
    sql = (
        "SELECT f.doc_id, d.path, f.chunk_index,"
        " snippet(chunks_fts, 1, '[', ']', ' … ', 12) AS snip,"
        " bm25(chunks_fts) AS score"
        " FROM chunks_fts f JOIN documents d ON d.doc_id = f.doc_id"
        " WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?"
    )
    rows = conn.execute(sql, [fts_query, limit]).fetchall()
    return [Hit(doc_id=r[0], path=r[1], chunk_index=r[2], snippet=r[3], score=r[4]) for r in rows]


def pass_at_k(conn: sqlite3.Connection, k: int) -> tuple[int, int, list[str]]:
    hit_count = 0
    misses: list[str] = []
    for q, expected_path in GOLD_QUERIES:
        fts_query = query.to_fts_query(q)
        hits = _search(conn, fts_query, limit=k)
        expected_doc_id = _doc_id(expected_path)
        if any(h.doc_id == expected_doc_id for h in hits):
            hit_count += 1
        else:
            misses.append(q)
    return hit_count, len(GOLD_QUERIES), misses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    print(f"クエリ数: {len(GOLD_QUERIES)} / k={args.k} / chunk_size={CHUNK_SIZE}\n")

    baseline_conn = _build_raw_index(use_context=False)
    baseline_hit, total, baseline_misses = pass_at_k(baseline_conn, args.k)
    print(f"[baseline]   Pass@{args.k}: {baseline_hit}/{total}")
    if baseline_misses:
        print(f"  失敗クエリ: {baseline_misses}")

    print("\ncontextual prefix 生成中（Ollama呼び出し）...")
    contextual_conn = _build_raw_index(use_context=True)
    contextual_hit, _, contextual_misses = pass_at_k(contextual_conn, args.k)
    print(f"[contextual] Pass@{args.k}: {contextual_hit}/{total}")
    if contextual_misses:
        print(f"  失敗クエリ: {contextual_misses}")

    print(f"\n差分: {contextual_hit - baseline_hit:+d} / {total}")


if __name__ == "__main__":
    main()
