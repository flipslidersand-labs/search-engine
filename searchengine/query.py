"""最小クエリパーサー（設計書 §2.9）。

ユーザー入力を FTS5 の MATCH 構文へ変換する。
対応構文:
  - フレーズ検索  : "機械学習 モデル"
  - ブーリアン    : AND / OR / NOT（大文字小文字非依存）
  - フィールド検索: type:code  path:sample （検索前にフィルタとして抽出）
  - それ以外の語は形態素分割して AND 結合
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import tokenizer

_PHRASE = re.compile(r'"([^"]+)"')
_BOOL = {"and": "AND", "or": "OR", "not": "NOT"}
# フィールド検索: フレーズ外の `key:value`（value はクォート可）
_FIELD = re.compile(r'(?<!\S)(type|path):("[^"]+"|\S+)')
_FIELDS = {"type", "path"}

# 疑問文語尾パターン: FTS クエリ生成前に除去してキーワード部分のみ残す (#69)
# raw（ベクトル検索用）には適用しない
_QUESTION_SUFFIX = re.compile(
    r"[\s　]*("
    r"とは何ですか|とは何か|って何ですか|って何|でしょうか|ですか|でしょう"
    r"|について教えてください|について教えて|について|とは"
    r"|ください|教えてください|教えて"
    r")[？?。\s]*$"
)


@dataclass
class ParsedQuery:
    fts: str  # FTS5 MATCH 文字列
    raw: str = ""  # フィールド除去後の自然文（ベクトル検索用）
    filters: dict[str, str] = field(default_factory=dict)


def parse(user_query: str) -> ParsedQuery:
    """フィールドフィルタを抽出し、残りを FTS5 クエリ + 自然文へ変換。"""
    filters: dict[str, str] = {}

    def _grab(m: re.Match) -> str:
        filters[m.group(1)] = m.group(2).strip('"')
        return " "

    remaining = _FIELD.sub(_grab, user_query)
    raw = remaining.replace('"', " ")
    for op in (" AND ", " OR ", " NOT ", " and ", " or ", " not "):
        raw = raw.replace(op, " ")
    raw = " ".join(raw.split())
    # FTS 用クエリは疑問文語尾を除去してキーワード部分のみ使う (#69)
    fts_input = _QUESTION_SUFFIX.sub("", remaining).strip() or remaining
    return ParsedQuery(fts=to_fts_query(fts_input), raw=raw, filters=filters)


def _word_tokens(text: str) -> list[str]:
    """unicode61 で語にならない（英数字・かな漢字を含まない）トークンを捨てる (#169)。"""
    return [t for t in tokenizer.tokenize(text) if any(c.isalnum() for c in t)]


def _quote_terms(text: str) -> list[str]:
    """生テキストを形態素分割し、各語を FTS5 用にクォート。"""
    out = []
    for tok in _word_tokens(text):
        # FTS5 の特殊文字を避けるため二重引用符で包む
        out.append('"' + tok.replace('"', "") + '"')
    return out


def to_fts_query(user_query: str) -> str:
    """ユーザークエリ → FTS5 MATCH 文字列。"""
    parts: list[str] = []
    pos = 0
    for m in _PHRASE.finditer(user_query):
        # フレーズ前の通常部分を処理
        before = user_query[pos : m.start()]
        parts.extend(_emit_tokens(before))
        # フレーズはトークン化して NEAR 的に連結（順序保持の "a b" 形式）
        phrase_tokens = _word_tokens(m.group(1))
        if phrase_tokens:
            parts.append('"' + " ".join(phrase_tokens) + '"')
        pos = m.end()
    parts.extend(_emit_tokens(user_query[pos:]))

    # 空なら全ヒット回避のため非マッチ語を返す
    if not [p for p in parts if p not in ("AND", "OR", "NOT")]:
        return '""'
    return _join(parts) or '""'


def _emit_tokens(text: str) -> list[str]:
    result: list[str] = []
    for word in text.split():
        low = word.lower()
        if low in _BOOL:
            result.append(_BOOL[low])
        else:
            # 1 語 = 1 要素（bigram 全体を AND 連結した群）。群単位で NOT を扱うため (#169)
            terms = _quote_terms(word)
            if terms:
                result.append(" AND ".join(terms))
    return result


def _join(parts: list[str]) -> str:
    """演算子が無い隣接語は暗黙 AND で連結。"""
    out: list[str] = []
    for p in _normalize_ops(parts):
        if out and p not in _OPS and out[-1] not in _OPS:
            out.append("AND")
        out.append(p)
    return " ".join(out)


_OPS = ("AND", "OR", "NOT")


def _normalize_ops(parts: list[str]) -> list[str]:
    """FTS5 構文エラーになる演算子配置を除去する (#127)。

    先頭/末尾の演算子を落とし、連続する演算子は最後の1つに畳む。
    FTS5 は `a AND NOT b` を受け付けないため、連続の末尾が NOT なら NOT のみ残す。
    """
    out: list[str] = []
    for p in parts:
        if p in _OPS:
            if not out:
                if p == "NOT":
                    out.append(p)  # 先頭 NOT は後段で意味を保って並べ替える
                continue
            if out[-1] in _OPS:
                out[-1] = p
                continue
        out.append(p)
    while out and out[-1] in _OPS:
        out.pop()
    while out and out[0] in ("AND", "OR"):
        out.pop(0)
    if out and out[0] == "NOT":
        # FTS5 は先頭 NOT 不可。先頭の NOT 句をすべて後ろへ回す:
        #   `NOT a NOT b c` → `c NOT a NOT b`。肯定語が無ければ空。
        # 先頭 NOT 句の直後の AND/OR は捨てる（`NOT a OR b` → `b NOT a`）。
        negs: list[str] = []
        while len(out) >= 2 and out[0] == "NOT" and out[1] not in _OPS:
            neg = out[1]
            negs.append(f"({neg})" if " AND " in neg else neg)
            out = out[2:]
        while out and out[0] in ("AND", "OR"):
            out.pop(0)
        if not out or out[0] == "NOT" or not negs:
            return []
        for n in negs:
            out += ["NOT", n]
    return out
