"""入口(HTTP / MCP)共通のパス検証。"""

from __future__ import annotations

import os
from pathlib import Path


class PathNotAllowedError(PermissionError):
    """ALLOWED_INDEX_DIRS の範囲外、または未設定。"""


def allowed_index_dirs() -> list[Path]:
    """ALLOWED_INDEX_DIRS を resolve 済みの Path 一覧で返す(未設定は空)。"""
    raw = os.environ.get("ALLOWED_INDEX_DIRS", "")
    return [Path(d.strip()).resolve() for d in raw.split(":") if d.strip()]


def validate_index_path(path: str) -> None:
    """ALLOWED_INDEX_DIRS の範囲外パスを拒否する(未設定は fail-closed)。"""
    if not os.environ.get("ALLOWED_INDEX_DIRS", ""):
        raise PathNotAllowedError("ALLOWED_INDEX_DIRS が未設定です")
    resolved = Path(path).resolve()
    if any(resolved.is_relative_to(d) for d in allowed_index_dirs()):
        return
    raise PathNotAllowedError(f"許可されていないパス: {path}")
