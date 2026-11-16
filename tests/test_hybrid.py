"""hybrid.rrf_merge / hybrid.search の単体テスト (#174)。

Hit を直接組んで RRF の仕様 (k=60, rank は 0 始まり) を検証する。Index は :memory: のみ。
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from searchengine import hybrid, query
from searchengine.embedder import Embedder
from searchengine.index import Hit, Index
from searchengine.query import ParsedQuery


def _hit(doc: str, chunk: int = 0, snippet: str = "", score: float = 0.0) -> Hit:
    return Hit(
        doc_id=doc, path=f"/x/{doc}.md", chunk_index=chunk, snippet=snippet or doc, score=score
    )


def test_rrf_duplicate_scores_added():
    # keyword 先頭 (rank0) + vector 2 位 (rank1) → 1/60 + 1/61
    a, b = _hit("a"), _hit("b")
    fused = hybrid.rrf_merge([a], [b, _hit("a")])
    by_doc = {f.hit.doc_id: f.rrf for f in fused}
    assert len(fused) == 2
    assert by_doc["a"] == pytest.approx(1 / 60 + 1 / 61)
    assert by_doc["b"] == pytest.approx(1 / 60)
    assert fused[0].hit.doc_id == "a"


def test_rrf_same_doc_different_chunk_not_merged():
    fused = hybrid.rrf_merge([_hit("a", 0)], [_hit("a", 1)])
    assert len(fused) == 2
    assert all(f.rrf == pytest.approx(1 / 60) for f in fused)


def test_rrf_first_hit_wins_for_display():
    kw = _hit("a", snippet="keyword-side")
    vec = _hit("a", snippet="vector-side")
    fused = hybrid.rrf_merge([kw], [vec])
    assert len(fused) == 1
    assert fused[0].hit.snippet == "keyword-side"


def test_rrf_custom_k():
    fused = hybrid.rrf_merge([_hit("a")], [_hit("a")], k=10)
    assert fused[0].rrf == pytest.approx(2 / 10)


def test_rrf_limit_truncates():
    fused = hybrid.rrf_merge([_hit("a"), _hit("b")], [_hit("c")], limit=1)
    assert len(fused) == 1


def test_rrf_limit_larger_than_candidates():
    fused = hybrid.rrf_merge([_hit("a")], [_hit("b")], limit=10)
    assert len(fused) == 2


def test_rrf_keyword_only():
    fused = hybrid.rrf_merge([_hit("a"), _hit("b")], [])
    assert [f.hit.doc_id for f in fused] == ["a", "b"]
    assert fused[0].rrf == pytest.approx(1 / 60)
    assert fused[1].rrf == pytest.approx(1 / 61)


def test_rrf_vector_only():
    fused = hybrid.rrf_merge([], [_hit("a"), _hit("b")])
    assert [f.hit.doc_id for f in fused] == ["a", "b"]


def test_rrf_both_empty():
    assert hybrid.rrf_merge([], []) == []


def test_rrf_descending_order():
    # b は両方に出るので a より上位
    fused = hybrid.rrf_merge([_hit("a"), _hit("b")], [_hit("b")])
    assert [f.hit.doc_id for f in fused] == ["b", "a"]
    scores = [f.rrf for f in fused]
    assert scores == sorted(scores, reverse=True)


def test_rrf_tie_order_is_stable():
    # a: keyword rank0, b: vector rank0 は同点。先に挿入された keyword 側が先 (sort は安定)
    fused = hybrid.rrf_merge([_hit("a")], [_hit("b")])
    assert fused[0].rrf == pytest.approx(fused[1].rrf)
    assert [f.hit.doc_id for f in fused] == ["a", "b"]
    # 繰り返しても同じ順序
    for _ in range(3):
        again = hybrid.rrf_merge([_hit("a")], [_hit("b")])
        assert [f.hit.doc_id for f in again] == ["a", "b"]


def test_search_without_embedder_keyword_only():
    idx = Index(":memory:")
    try:
        assert idx.vectors is None
        idx.add_document("/x/ml.md", "機械学習はデータからモデルを学習する分野である。")
        idx.add_document("/x/cook.md", "今日はカレーを作った。")
        fused = hybrid.search(idx, query.parse("機械学習"))
        assert fused and fused[0].hit.path.endswith("ml.md")
        assert fused[0].rrf == pytest.approx(1 / 60)
    finally:
        idx.close()


def test_search_empty_raw_skips_vector_search():
    idx = Index(":memory:", embedder=Embedder())
    try:
        idx.add_document("/x/ml.md", "機械学習はデータからモデルを学習する分野である。")
        base = query.parse("機械学習")
        parsed = ParsedQuery(fts=base.fts, raw="", filters={})
        with patch.object(Index, "vector_search") as vs:
            fused = hybrid.search(idx, parsed)
        vs.assert_not_called()
        assert fused and fused[0].rrf == pytest.approx(1 / 60)
    finally:
        idx.close()


def test_search_with_embedder_and_raw_calls_vector_search():
    idx = Index(":memory:", embedder=Embedder())
    try:
        idx.add_document("/x/ml.md", "機械学習はデータからモデルを学習する分野である。")
        parsed = query.parse("機械学習")
        with patch.object(Index, "vector_search", return_value=[]) as vs:
            hybrid.search(idx, parsed)
        vs.assert_called_once()
    finally:
        idx.close()
