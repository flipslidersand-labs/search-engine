"""Tests for searchengine.nugget module."""
from __future__ import annotations

from searchengine.nugget import bm25_scores, extract_nuggets, split_sentences


# ── split_sentences ───────────────────────────────────────────────────────────


def test_split_sentences_basic():
    text = "Hello world. This is a test. Final sentence."
    parts = split_sentences(text)
    assert len(parts) == 3
    assert parts[0] == "Hello world."
    assert parts[2] == "Final sentence."


def test_split_sentences_empty():
    assert split_sentences("") == []


def test_split_sentences_single():
    parts = split_sentences("Only one sentence here.")
    assert parts == ["Only one sentence here."]


def test_split_sentences_japanese():
    text = "これはテストです。次の文章です。最後の文。"
    parts = split_sentences(text)
    assert len(parts) == 3


def test_split_sentences_exclamation_question():
    text = "What is BM25? It is a ranking function! Learn more about it."
    parts = split_sentences(text)
    assert len(parts) == 3


# ── bm25_scores ───────────────────────────────────────────────────────────────


def test_bm25_scores_empty_sentences():
    assert bm25_scores("query", []) == []


def test_bm25_scores_returns_same_length():
    sentences = ["apple banana", "cherry date", "elderberry fig"]
    scores = bm25_scores("apple", sentences)
    assert len(scores) == len(sentences)


def test_bm25_scores_relevant_sentence_higher():
    sentences = [
        "BM25 is a ranking function used in information retrieval.",
        "The weather is sunny today.",
        "Machine learning models require training data.",
    ]
    scores = bm25_scores("BM25 ranking", sentences)
    # The first sentence should score highest
    assert scores[0] == max(scores)


def test_bm25_scores_all_floats():
    sentences = ["foo bar", "baz qux"]
    scores = bm25_scores("foo", sentences)
    assert all(isinstance(s, float) for s in scores)


# ── extract_nuggets ───────────────────────────────────────────────────────────


def test_extract_nuggets_selects_top_k():
    text = (
        "BM25 is a text ranking algorithm. "
        "It was developed for information retrieval. "
        "The weather today is nice. "
        "Cats are popular pets. "
        "BM25 uses term frequency and inverse document frequency."
    )
    result = extract_nuggets("BM25 algorithm", text, top_k=2)
    # Result should contain BM25-related content
    assert "BM25" in result


def test_extract_nuggets_preserves_order():
    text = "First sentence about apples. Second sentence about bananas. Third sentence about apples again."
    result = extract_nuggets("apples", text, top_k=2)
    # "First" should appear before "Third" in the result
    first_pos = result.find("First")
    third_pos = result.find("Third")
    assert first_pos != -1
    assert third_pos != -1
    assert first_pos < third_pos


def test_extract_nuggets_fallback_empty_text():
    result = extract_nuggets("query", "")
    assert result == ""


def test_extract_nuggets_single_sentence():
    text = "This is the only sentence."
    result = extract_nuggets("sentence", text, top_k=3)
    assert result == "This is the only sentence."


def test_extract_nuggets_top_k_gte_sentences():
    text = "First sentence. Second sentence."
    result = extract_nuggets("first second", text, top_k=10)
    # When top_k exceeds number of sentences, all sentences are returned
    assert "First sentence." in result
    assert "Second sentence." in result


def test_extract_nuggets_japanese():
    text = "BM25はランキング関数です。今日は天気が良いです。情報検索に使われます。"
    result = extract_nuggets("BM25 ランキング", text, top_k=2)
    assert result  # Should return non-empty result


def test_extract_nuggets_returns_string():
    text = "Hello world. This is a test."
    result = extract_nuggets("hello", text, top_k=1)
    assert isinstance(result, str)
