"""文書取込（設計書 §2.1）。

Phase 1 は Markdown / テキスト / コードのプレーン読み込みを対象とする。
PDF・メールは Phase 1 では拡張ポイントとして関数を用意のみ。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .security import is_within

logger = logging.getLogger(__name__)

TEXT_EXTS = {
    ".md": "markdown",
    ".txt": "text",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".json": "code",
    ".rs": "code",
}


def detect_type(path: str) -> str | None:
    return TEXT_EXTS.get(os.path.splitext(path)[1].lower())


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def iter_files(root: str, allowed: list[Path] | None = None):
    """対応拡張子のファイルを再帰列挙。

    allowed を渡すと、symlink を解決した実体がその範囲外のファイルはスキップする
    (単一ファイル指定にも適用)。None は検査なし(CLI などローカル信頼の呼び出し用)。
    HTTP / MCP は必ず allowed_index_dirs() を渡すこと。
    """
    if os.path.isfile(root):
        if detect_type(root):
            if allowed is not None and not is_within(root, allowed):
                logger.warning("許可範囲外のファイルをスキップ: %r", root)
                return
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # ノイズディレクトリを除外
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
        for name in filenames:
            full = os.path.join(dirpath, name)
            if not detect_type(full):
                continue
            if allowed is not None and not is_within(full, allowed):
                logger.warning("許可範囲外を指す symlink をスキップ: %r", full)
                continue
            yield full
