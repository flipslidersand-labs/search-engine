"""`.env.example` / README の環境変数表とコードの整合を守るテスト。"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_ENV_RE = re.compile(r"""(?:environ\.get|getenv)\(\s*["']([A-Z][A-Z0-9_]*)["']""")


def _code_env_vars() -> set[str]:
    names: set[str] = set()
    for py in (ROOT / "searchengine").rglob("*.py"):
        names |= set(_ENV_RE.findall(py.read_text(encoding="utf-8")))
    return names


def _env_example_keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        m = re.match(r"([A-Z][A-Z0-9_]*)=(.*)$", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def test_code_scan_finds_vars():
    assert "ALLOWED_INDEX_DIRS" in _code_env_vars()


def test_env_example_has_required_allowed_index_dirs():
    keys = _env_example_keys()
    assert keys.get("ALLOWED_INDEX_DIRS"), "ALLOWED_INDEX_DIRS must be set to a value"


def test_env_example_covers_code_env_vars():
    missing = _code_env_vars() - set(_env_example_keys())
    assert not missing, f".env.example に不足: {sorted(missing)}"


def test_readme_table_covers_code_env_vars():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([A-Z][A-Z0-9_]*)` \|", readme, re.M))
    missing = _code_env_vars() - documented
    assert not missing, f"README 環境変数表に不足: {sorted(missing)}"
