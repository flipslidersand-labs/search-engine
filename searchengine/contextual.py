"""Contextual prefix 生成（Contextual Retrieval、#78/#82）。

チャンク単体では文書内の位置づけ・文脈が失われ検索失敗率が上がる問題に対し、
各チャンクの前に「このチャンクは文書のどこに位置するか」を要約した短い説明を
前置する。LLM呼び出しは `searchengine/llm.py` の OllamaClient を再利用する
（Claude API 直接キー使用は禁止のため、ローカルLLMで代替）。
生成に失敗しても取り込み全体を止めないよう、失敗時は元のチャンクをそのまま返す。
"""

from __future__ import annotations

import logging

from .chunker import Chunk
from .llm import Message, OllamaClient

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """以下は文書全体と、そこから抽出した1つのチャンクです。
このチャンクが文書全体の中でどのような位置づけ・文脈にあるかを、
検索用の短い説明として1〜2文で日本語要約してください。
説明のみを出力し、前置き・見出しは不要です。

# 文書全体
{document}

# チャンク
{chunk}
"""


def generate_context(
    document: str, chunk_text: str, client: OllamaClient | None = None
) -> str | None:
    """1チャンク分の contextual prefix を生成する。失敗時は None を返す。"""
    client = client or OllamaClient()
    prompt = _PROMPT_TEMPLATE.format(document=document, chunk=chunk_text)
    try:
        result = client.chat([Message(role="user", content=prompt)])
        text = result.content.strip()
        return text or None
    except Exception as e:
        logger.warning("contextual prefix生成に失敗、prefixなしで続行: %s", e)
        return None


def add_context(
    document: str, chunks: list[Chunk], client: OllamaClient | None = None
) -> list[Chunk]:
    """各チャンクに contextual prefix を前置した新しい Chunk リストを返す。

    生成に失敗したチャンクは prefix なし（元のテキストのまま）になる。
    """
    client = client or OllamaClient()
    result: list[Chunk] = []
    for c in chunks:
        context = generate_context(document, c.text, client=client)
        text = f"{context}\n\n{c.text}" if context else c.text
        result.append(Chunk(index=c.index, text=text))
    return result
