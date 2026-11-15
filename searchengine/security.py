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


def is_within(path: str, allowed: list[Path]) -> bool:
    """path を resolve した実体が allowed のどれかの配下なら True。"""
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(d) for d in allowed)


def validate_index_path(path: str) -> None:
    """ALLOWED_INDEX_DIRS の範囲外パスを拒否する(未設定・空指定は fail-closed)。"""
    dirs = allowed_index_dirs()
    if not dirs:
        raise PathNotAllowedError("ALLOWED_INDEX_DIRS が未設定です")
    if not is_within(path, dirs):
        raise PathNotAllowedError(f"許可されていないパス: {path}")
