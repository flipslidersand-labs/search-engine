"""e5 の512 tokens上限ガード (#95) のテスト。"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from searchengine import chunker
from searchengine.chunker import (
    EMBED_TOKEN_BUDGET,
    MAX_CONTEXT_TOKENS,
    Chunk,
    estimate_tokens,
    split_to_token_budget,
    truncate_to_tokens,
)
from searchengine.contextual import generate_context
from searchengine.index import Index

JA = "これは検索エンジンの障害対応手順です。" * 200  # 空白なし: 語数ベースでは1語扱い
EN = "The quick brown fox jumps over the lazy dog. " * 200


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s)


def test_estimate_counts_cjk_words_and_punct():
    assert estimate_tokens("検索") == 2
    assert estimate_tokens("hello world") == 4
    assert estimate_tokens("a,b") == 5  # 2語 + 記号1


@pytest.mark.parametrize("text", [JA, EN])
def test_split_respects_budget_and_keeps_content(text):
    out = split_to_token_budget([Chunk(0, text)])
    assert len(out) > 1
    assert all(estimate_tokens(c.text) <= EMBED_TOKEN_BUDGET for c in out)
    assert [c.index for c in out] == list(range(len(out)))
    assert _nospace("".join(c.text for c in out)) == _nospace(text)


def test_split_leaves_small_chunks_untouched():
    chunks = [Chunk(0, "短い"), Chunk(1, "short text")]
    out = split_to_token_budget(chunks)
    assert [c.text for c in out] == ["短い", "short text"]


def test_split_prefers_sentence_boundaries():
    out = split_to_token_budget([Chunk(0, JA)])
    assert all(c.text.endswith("。") for c in out)


def test_split_handles_unbreakable_long_word():
    out = split_to_token_budget([Chunk(0, "x" * 5000)])
    assert all(estimate_tokens(c.text) <= EMBED_TOKEN_BUDGET for c in out)


def test_truncate_to_tokens_boundary():
    t = truncate_to_tokens(JA, 50)
    assert estimate_tokens(t) <= 50 and estimate_tokens(t + JA[len(t)]) > 50
    assert truncate_to_tokens("短い", 50) == "短い"


def test_generate_context_caps_prefix_length():
    m = MagicMock()
    m.raise_for_status = MagicMock()
    m.json.return_value = {"message": {"content": "説明" * 500}}
    with patch("httpx.post", return_value=m):
        ctx = generate_context("doc", "chunk")
    assert estimate_tokens(ctx) <= MAX_CONTEXT_TOKENS


class _RecordingEmbedder:
    def __init__(self):
        self.inputs: list[str] = []

    def encode(self, texts, mode="index"):
        import numpy as np

        self.inputs.extend(texts)
        return np.zeros((len(texts), 8), dtype="float32")


def test_index_with_embedder_keeps_embedding_inputs_within_budget(tmp_path):
    emb = _RecordingEmbedder()
    idx = Index(str(tmp_path / "t.db"), embedder=emb)
    idx.add_document("a.md", JA + "\n\n" + EN)
    assert emb.inputs
    assert all(estimate_tokens(t) <= EMBED_TOKEN_BUDGET for t in emb.inputs)


def test_index_with_contextual_prefix_reserves_room(tmp_path):
    emb = _RecordingEmbedder()
    idx = Index(str(tmp_path / "t.db"), embedder=emb, use_contextual_prefix=True)
    prefix = "文脈" * 500
    m = MagicMock()
    m.raise_for_status = MagicMock()
    m.json.return_value = {"message": {"content": prefix}}
    with patch("httpx.post", return_value=m):
        idx.add_document("a.md", JA)
    assert all(estimate_tokens(t) <= EMBED_TOKEN_BUDGET for t in emb.inputs)


def test_index_without_embedder_keeps_chunking_unchanged(tmp_path):
    idx = Index(str(tmp_path / "t.db"))
    idx.add_document("a.md", JA)
    n = idx.conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
    assert n == len(chunker.chunk_text(JA))


def test_estimate_is_conservative_against_real_e5_tokenizer():
    """実 tokenizer（ローカルHFキャッシュ）で、推定が実測を 14% 超えて下回らないこと。"""
    import os

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-base")
    except Exception:
        pytest.skip("e5 tokenizer unavailable")
    docs = Path(__file__).resolve().parent.parent / "docs"
    samples = [JA[:600], EN[:600]] + [
        p.read_text(encoding="utf-8")[:1500] for p in sorted(docs.glob("*.md"))
    ]
    for s in samples:
        real = len(tok(s, add_special_tokens=False)["input_ids"])
        assert real <= estimate_tokens(s) * 1.14, (real, estimate_tokens(s))
