"""チャンキング（設計書 §2.2）。

長文の局所内容を検索可能にするため、文書をチャンク単位に分割する。
段落・見出し境界を優先し、無ければトークン数で分割。
オーバーラップを設けて境界での文脈断絶を防ぐ。

注: トークン長は estimate_tokens（CJK 1/字・英数語 2/語・記号 1/字）で近似する。
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
_TOKEN = re.compile(rf"(?P<cjk>{_CJK.pattern})|(?P<word>[A-Za-z0-9]+)|(?P<punct>[^\sA-Za-z0-9])")
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
    """推定 tokens が budget 以下になる最長の先頭部分を返す（1 パス・長さに比例）。"""
    used = 0
    for m in _TOKEN.finditer(text):
        used += 2 if m.lastgroup == "word" else 1
        if used > budget:
            return text[: m.start()]
    return text


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
    # 行頭インデントを保つため strip() ではなく前後の改行のみ除く
    parts = [p.strip("\n") for p in text.split("\n\n")]
    return [p for p in parts if p.strip()]


def _window_split(para: str, size: int, overlap: int) -> list[str]:
    """段落を推定 tokens の窓でスライド分割する。元テキストを切り出すので改行・インデントは保持される。"""
    toks = [(m.start(), m.end(), 2 if m.lastgroup == "word" else 1) for m in _TOKEN.finditer(para)]
    out: list[str] = []
    i = 0
    while i < len(toks):
        j, used = i, 0
        while j < len(toks) and (j == i or used + toks[j][2] <= size):
            used += toks[j][2]
            j += 1
        out.append(para[toks[i][0] : toks[j - 1][1]])
        if j >= len(toks):
            break
        # 末尾から overlap 分を次窓の先頭に戻す(必ず前進する)
        k, back = j, 0
        while k > i + 1 and back + toks[k - 1][2] <= overlap:
            back += toks[k - 1][2]
            k -= 1
        i = k
    return out


def chunk_text(text: str, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    """段落優先 + トークン数フォールバックで分割。

    size / overlap は estimate_tokens の推定 tokens 単位。段落内の改行・インデントは保持し、
    段落同士は空行で連結する。
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0

    def flush() -> None:
        if buf:
            chunks.append(Chunk(index=len(chunks), text="\n\n".join(buf)))

    for para in _split_paragraphs(text) or [text]:
        if not para.strip():
            continue
        n = estimate_tokens(para)
        # 段落がチャンクサイズに収まるならそのまま積む
        if buf_tokens + n <= size:
            buf.append(para)
            buf_tokens += n
            continue
        # バッファを確定し、長い段落はトークン窓でスライド分割
        flush()
        buf, buf_tokens = [], 0
        if n <= size:
            buf, buf_tokens = [para], n
            continue
        for piece in _window_split(para, size, overlap):
            chunks.append(Chunk(index=len(chunks), text=piece))
    flush()

    # 全体が空ならフォールバックで1チャンク
    if not chunks and text.strip():
        chunks.append(Chunk(index=0, text=text.strip()))
    return chunks
