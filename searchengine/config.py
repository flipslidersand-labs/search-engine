"""設定読み取りと Index 生成の共通ファクトリ（#140）。

server / mcp_server / cli が同じ設定（contextual prefix・embedder）で Index を作るための
単一の入口。環境変数は呼び出し時に読む（import 時評価をしないのでテストで monkeypatch しやすい）。
"""

from __future__ import annotations

import os

from .index import Index

_TRUTHY = ("1", "true", "yes")


def contextual_prefix_enabled() -> bool:
    """SEARCH_ENGINE_CONTEXTUAL_PREFIX が真値かを返す。"""
    return os.environ.get("SEARCH_ENGINE_CONTEXTUAL_PREFIX", "").lower() in _TRUTHY


def open_index(db: str, want_vector: bool = False) -> Index:
    """全入口共通の Index ファクトリ。"""
    embedder = None
    if want_vector:
        from .embedder import create_embedder  # numpy 依存。必要時のみ import

        embedder = create_embedder()
    return Index(db, embedder=embedder, use_contextual_prefix=contextual_prefix_enabled())
