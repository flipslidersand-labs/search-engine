"""tokenize / nugget._tokenize の出力固定（drop_stopwords 削除リファクタの回帰用）。"""

from __future__ import annotations

import pytest

from searchengine import nugget, tokenizer

_FALLBACK = pytest.mark.skipif(tokenizer._HAS_FUGASHI, reason="fallback 実装の出力を固定")


@_FALLBACK
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("機械学習のモデル", ["機械", "械学", "学習", "習の", "のモ", "モデ", "デル"]),
        ("Hello, World_1 とは", ["hello", "world_1", "とは"]),
        ("の は が", []),
        ("A a A", ["a"]),
        ("", []),
    ],
)
def test_tokenize_fallback_pinned(text, expected):
    assert tokenizer.tokenize(text) == expected


def test_tokenize_always_drops_stopwords():
    assert tokenizer.tokenize("の") == []
    assert tokenizer.tokenize("の は が を") == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello World foo", ["hello", "world", "foo"]),
        ("機械学習のモデル", ["機械", "械学", "学習", "習の", "のモ", "モデ", "デル"]),
        ("A a A.", ["a", "a", "a."]),
        ("の", ["の"]),
        ("", []),
    ],
)
def test_nugget_tokenize_pinned(text, expected):
    assert nugget._tokenize(text) == expected
