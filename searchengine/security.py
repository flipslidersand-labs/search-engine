"""入口(HTTP / MCP)共通のパス検証。"""

from __future__ import annotations

import os
from pathlib import Path


class PathNotAllowedError(PermissionError):
    """ALLOWED_INDEX_DIRS の範囲外、または未設定。"""


def validate_index_path(path: str) -> None:
    """ALLOWED_INDEX_DIRS の範囲外パスを拒否する(未設定は fail-closed)。"""
    allowed_raw = os.environ.get("ALLOWED_INDEX_DIRS", "")
    if not allowed_raw:
        raise PathNotAllowedError("ALLOWED_INDEX_DIRS が未設定です")
    resolved = Path(path).resolve()
    for d in allowed_raw.split(":"):
        d = d.strip()
        if d and resolved.is_relative_to(Path(d).resolve()):
            return
    raise PathNotAllowedError(f"許可されていないパス: {path}")
