"""チャンキング（設計書 §2.2）。

長文の局所内容を検索可能にするため、文書をチャンク単位に分割する。
段落・見出し境界を優先し、無ければトークン数で分割。
オーバーラップを設けて境界での文脈断絶を防ぐ。

注: トークン長は簡易に「空白区切り語数」で近似する（Phase 1 MVP）。
本番では tokenizer の出力長やモデルの tokenizer に合わせる。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_SIZE = 512
DEFAULT_OVERLAP = 64

# embedding 入力の token 上限ガード (#95)。e5 の上限は 512 tokens（`passage: `・特殊トークン込み）で、
# 超過分は embedding-svc が黙って切り詰める。`estimate_tokens` は stdlib のみの保守的推定
# （e5 tokenizer 実測 293 サンプルで過小評価 1%、実測/推定の最大比 1.14）なので、
# 推定値の予算は 512 ÷ 1.14 ≒ 440 とする。
EMBED_TOKEN_BUDGET = 440
# contextual prefix に割く推定 tokens の上限（合計予算の内数）
MAX_CONTEXT_TOKENS = 100

_CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
_WORD = re.compile(r"[A-Za-z0-9]+")
_PUNCT = re.compile(r"[^\sA-Za-z0-9]")
_SENTENCE = re.compile(r"[^。！？!?\n]*?(?:[。！？!?\n]|\.(?=\s))|[^。！？!?\n]+$")


@dataclass
class Chunk:
    index: int
    text: str


def estimate_tokens(text: str) -> int:
    """e5 系 tokenizer の token 数を保守的に推定（CJK 1/字、英数語 2/語、記号 1/字）。"""
    cjk = len(_CJK.findall(text))
    rest = _CJK.sub(" ", text)
    return cjk + 2 * len(_WORD.findall(rest)) + len(_PUNCT.findall(rest))


def truncate_to_tokens(text: str, budget: int) -> str:
    """推定 tokens が budget 以下になる最長の先頭部分を返す。"""
    if estimate_tokens(text) <= budget:
        return text
    lo, hi = 0, len(text)
    while lo < hi:  # 推定値は文字を足すと単調非減少
        mid = (lo + hi + 1) // 2
        if estimate_tokens(text[:mid]) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo]


def _pieces(text: str, budget: int) -> list[str]:
    """文境界で分割し、なお budget 超の文は文字単位で分割する。"""
    out: list[str] = []
    for sent in _SENTENCE.findall(text):
        while estimate_tokens(sent) > budget:
            head = truncate_to_tokens(sent, budget) or sent[:1]
            out.append(head)
            sent = sent[len(head) :]
        if sent:
            out.append(sent)
    return out


def split_to_token_budget(chunks: list[Chunk], budget: int = EMBED_TOKEN_BUDGET) -> list[Chunk]:
    """推定 tokens が budget を超えるチャンクを文境界（無ければ文字単位）で分割する。

    収まるチャンクはそのまま。分割後は index を振り直す。
    """
    result: list[str] = []
    for c in chunks:
        if estimate_tokens(c.text) <= budget:
            result.append(c.text)
            continue
        buf, used = "", 0
        for piece in _pieces(c.text, budget):
            n = estimate_tokens(piece)
            if buf and used + n > budget:
                result.append(buf.strip())
                buf, used = "", 0
            buf += piece
            used += n
        if buf.strip():
            result.append(buf.strip())
    return [Chunk(index=i, text=t) for i, t in enumerate(t for t in result if t)]


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def chunk_text(text: str, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    """段落優先 + トークン数フォールバックで分割。"""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[Chunk] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            chunks.append(Chunk(index=len(chunks), text=" ".join(buf)))

    for para in _split_paragraphs(text) or [text]:
        words = para.split()
        if not words:
            continue
        # 段落がチャンクサイズに収まるならそのまま積む
        if len(buf) + len(words) <= size:
            buf.extend(words)
            continue
        # バッファを確定し、長い段落はトークン窓でスライド分割
        flush()
        buf = []
        if len(words) <= size:
            buf = words
            continue
        step = size - overlap
        for start in range(0, len(words), step):
            window = words[start : start + size]
            if not window:
                break
            chunks.append(Chunk(index=len(chunks), text=" ".join(window)))
            if start + size >= len(words):
                break
    flush()

    # 全体が空ならフォールバックで1チャンク
    if not chunks and text.strip():
        chunks.append(Chunk(index=0, text=text.strip()))
    return chunks
