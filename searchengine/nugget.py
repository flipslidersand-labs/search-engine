"""Nugget extraction: select query-relevant sentences from a chunk.

Based on the CoinRAG idea: instead of returning full chunks to the LLM,
return only the top-N sentences most relevant to the query (nuggets).
"""

from __future__ import annotations

import math
import re
from collections import Counter


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s*", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _tokenize(text: str) -> list[str]:
    ascii_ratio = sum(1 for c in text if c.isascii()) / max(len(text), 1)
    if ascii_ratio > 0.5:
        return text.lower().split()
    # CJK: character bigrams
    text = text.lower().replace(" ", "")
    return [text[i : i + 2] for i in range(len(text) - 1)] if len(text) >= 2 else list(text)


def bm25_scores(query: str, sentences: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    if not sentences:
        return []
    tokenized = [_tokenize(s) for s in sentences]
    avgdl = sum(len(t) for t in tokenized) / len(tokenized)
    q_terms = _tokenize(query)
    scores = []
    for doc in tokenized:
        tf = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in q_terms:
            f = tf.get(term, 0)
            idf = math.log(1 + (len(sentences) - f + 0.5) / (f + 0.5))
            numerator = f * (k1 + 1)
            denominator = f + k1 * (1 - b + b * dl / max(avgdl, 1))
            score += idf * (numerator / denominator)
        scores.append(score)
    return scores


def extract_nuggets(query: str, text: str, top_k: int = 3) -> str:
    """Return the top-k most query-relevant sentences from text joined as a string.

    Preserves original document order for the selected sentences.
    Falls back to the full text if it cannot be split into sentences.
    """
    sentences = split_sentences(text)
    if not sentences:
        return text
    scores = bm25_scores(query, sentences)
    # Pick top-k by score, then re-sort by original position
    top_indices = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)[:top_k]
    ordered = sorted(top_indices)
    return " ".join(sentences[i] for i in ordered)
