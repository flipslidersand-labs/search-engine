"""検索エンジン共通の例外階層。

API 層(server.py)が例外型でステータスを決められるようにする。
このモジュールは他の searchengine モジュールを import しない(循環回避)。
"""

from __future__ import annotations


class SearchEngineError(Exception):
    """searchengine 由来の想定済みエラーの基底。"""


class VectorIndexUnavailableError(SearchEngineError, RuntimeError):
    """ベクトル検索を要求されたが、Index にベクトル(embedder)が無い。

    既存の ``except RuntimeError`` を壊さないよう RuntimeError も継承する。
    """
