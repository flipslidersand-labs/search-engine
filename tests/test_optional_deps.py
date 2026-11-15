"""任意依存が requirements-optional.txt に宣言されていることの突き合わせ。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPTIONAL = ROOT / "requirements-optional.txt"

# コード中の任意 import のトップレベルモジュール -> PyPI パッケージ名
MODULE_TO_PACKAGE = {
    "qdrant_client": "qdrant-client",
    "openpyxl": "openpyxl",
    "google": "google-auth",
    "googleapiclient": "google-api-python-client",
    "google_auth_oauthlib": "google-auth-oauthlib",
    "fugashi": "fugashi",
}
# fugashi は辞書が無いと Tagger() が失敗しフォールバックするため必須
EXTRA_PACKAGES = {"unidic-lite"}


def _declared() -> dict[str, str]:
    assert OPTIONAL.exists(), "requirements-optional.txt がありません"
    out: dict[str, str] = {}
    for line in OPTIONAL.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"([A-Za-z0-9_.-]+)(\[[^\]]*\])?(.*)", line)
        assert m, line
        out[m.group(1).lower()] = m.group(3).strip()
    return out


def test_optional_file_declares_all_packages_with_bounds():
    declared = _declared()
    for pkg in set(MODULE_TO_PACKAGE.values()) | EXTRA_PACKAGES:
        assert pkg in declared, f"{pkg} が未宣言"
        spec = declared[pkg]
        assert ">=" in spec and "<" in spec, f"{pkg} に上下限が必要: {spec!r}"


def test_every_guarded_import_in_code_is_declared():
    """try ブロック内 / 関数内の任意 import 対象が宣言と対応表に含まれる。"""
    src = ROOT / "searchengine"
    found: set[str] = set()
    pat = re.compile(r"^\s+(?:from|import)\s+(qdrant_client|openpyxl|google\w*|fugashi)\b", re.M)
    for py in src.rglob("*.py"):
        found.update(m.group(1) for m in pat.finditer(py.read_text(encoding="utf-8")))
    assert found, "任意 import が検出できない"
    unknown = found - set(MODULE_TO_PACKAGE)
    assert not unknown, f"対応表に無い任意 import: {unknown}"
    declared = _declared()
    for mod in found:
        assert MODULE_TO_PACKAGE[mod] in declared
