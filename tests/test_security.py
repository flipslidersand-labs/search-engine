"""security.is_within / validate_index_path / ingest.iter_files の境界テスト (#173)。"""

from __future__ import annotations

from pathlib import Path

import pytest

from searchengine import ingest
from searchengine.security import (
    PathNotAllowedError,
    allowed_index_dirs,
    is_within,
    validate_index_path,
)


@pytest.fixture
def dirs(tmp_path: Path) -> dict[str, Path]:
    a = tmp_path / "allowed"
    evil = tmp_path / "allowed-evil"
    b = tmp_path / "other"
    for d in (a, evil, b):
        d.mkdir()
    (a / "f.txt").write_text("a", encoding="utf-8")
    (evil / "f.txt").write_text("e", encoding="utf-8")
    (b / "f.txt").write_text("b", encoding="utf-8")
    return {"root": tmp_path, "a": a, "evil": evil, "b": b}


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink 非対応環境")


# --- is_within ---


def test_is_within_allowed_dir_itself(dirs):
    assert is_within(str(dirs["a"]), [dirs["a"]]) is True


def test_is_within_child_file(dirs):
    assert is_within(str(dirs["a"] / "f.txt"), [dirs["a"]]) is True


def test_is_within_nonexistent_child(dirs):
    """存在しないパスも resolve は成功し、配下なら True(strict ではない)。"""
    assert is_within(str(dirs["a"] / "nope" / "x.txt"), [dirs["a"]]) is True


def test_is_within_nonexistent_outside(dirs):
    assert is_within(str(dirs["root"] / "nope" / "x.txt"), [dirs["a"]]) is False


def test_is_within_rejects_prefix_sibling(dirs):
    assert is_within(str(dirs["evil"]), [dirs["a"]]) is False
    assert is_within(str(dirs["evil"] / "f.txt"), [dirs["a"]]) is False


def test_is_within_rejects_parent(dirs):
    assert is_within(str(dirs["root"]), [dirs["a"]]) is False


def test_is_within_empty_allowed(dirs):
    assert is_within(str(dirs["a"]), []) is False


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("allowed/f.txt", True),
        ("allowed/../allowed/f.txt", True),
        ("allowed/sub/../f.txt", True),
        ("allowed/../other/f.txt", False),
        ("allowed/..", False),
        ("allowed/../allowed-evil/f.txt", False),
    ],
)
def test_is_within_dotdot_absolute(dirs, rel, expected):
    assert is_within(str(dirs["root"] / rel), [dirs["a"]]) is expected


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("allowed/f.txt", True),
        ("allowed/../other/f.txt", False),
        ("other/f.txt", False),
    ],
)
def test_is_within_relative_path(dirs, monkeypatch, rel, expected):
    """相対パスは cwd 基準で resolve される。"""
    monkeypatch.chdir(dirs["root"])
    assert is_within(rel, [dirs["a"]]) is expected


def test_is_within_multiple_dirs(dirs):
    allowed = [dirs["a"], dirs["b"]]
    assert is_within(str(dirs["b"] / "f.txt"), allowed) is True
    assert is_within(str(dirs["a"] / "f.txt"), allowed) is True
    assert is_within(str(dirs["evil"] / "f.txt"), allowed) is False


def test_is_within_symlink_escape_rejected(dirs):
    link = dirs["a"] / "link.txt"
    _symlink(link, dirs["b"] / "f.txt")
    assert is_within(str(link), [dirs["a"]]) is False


def test_is_within_symlink_inside_allowed(dirs):
    link = dirs["a"] / "link.txt"
    _symlink(link, dirs["a"] / "f.txt")
    assert is_within(str(link), [dirs["a"]]) is True


def test_is_within_symlinked_dir_escape_rejected(dirs):
    link = dirs["a"] / "dirlink"
    _symlink(link, dirs["b"])
    assert is_within(str(link / "f.txt"), [dirs["a"]]) is False


# --- allowed_index_dirs / validate_index_path ---


def test_allowed_index_dirs_colon_separated(dirs, monkeypatch):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", f"{dirs['a']}: {dirs['b']} ::")
    assert allowed_index_dirs() == [dirs["a"].resolve(), dirs["b"].resolve()]


def test_allowed_index_dirs_unset(monkeypatch):
    monkeypatch.delenv("ALLOWED_INDEX_DIRS", raising=False)
    assert allowed_index_dirs() == []


def test_validate_unset_fails_closed(dirs, monkeypatch):
    monkeypatch.delenv("ALLOWED_INDEX_DIRS", raising=False)
    with pytest.raises(PathNotAllowedError, match="未設定"):
        validate_index_path(str(dirs["a"]))


@pytest.mark.parametrize(
    ("key", "ok"),
    [("a", True), ("b", True), ("evil", False), ("root", False)],
)
def test_validate_second_colon_entry_matches(dirs, monkeypatch, key, ok):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", f"{dirs['a']}:{dirs['b']}")
    if ok:
        validate_index_path(str(dirs[key] / "f.txt"))
    else:
        with pytest.raises(PathNotAllowedError, match="許可されていない"):
            validate_index_path(str(dirs[key]))


def test_validate_allowed_dir_itself_ok(dirs, monkeypatch):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(dirs["a"]))
    validate_index_path(str(dirs["a"]))


def test_validate_dotdot_rejected(dirs, monkeypatch):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(dirs["a"]))
    with pytest.raises(PathNotAllowedError):
        validate_index_path(str(dirs["a"] / ".." / "other" / "f.txt"))


def test_validate_nonexistent_outside_rejected(dirs, monkeypatch):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(dirs["a"]))
    with pytest.raises(PathNotAllowedError):
        validate_index_path(str(dirs["root"] / "missing" / "x.txt"))


# --- ingest.iter_files ---


def test_iter_files_allowed_none_does_not_filter_symlink(dirs):
    """allowed=None は検査なし(外部を指す symlink も列挙される)。"""
    link = dirs["a"] / "link.txt"
    _symlink(link, dirs["b"] / "f.txt")
    got = set(ingest.iter_files(str(dirs["a"]), None))
    assert got == {str(dirs["a"] / "f.txt"), str(link)}


def test_iter_files_allowed_none_single_file(dirs):
    f = str(dirs["b"] / "f.txt")
    assert list(ingest.iter_files(f)) == [f]


def test_iter_files_with_allowed_skips_symlink_escape(dirs):
    _symlink(dirs["a"] / "link.txt", dirs["b"] / "f.txt")
    got = set(ingest.iter_files(str(dirs["a"]), [dirs["a"]]))
    assert got == {str(dirs["a"] / "f.txt")}


def test_iter_files_with_allowed_single_file_outside(dirs):
    assert list(ingest.iter_files(str(dirs["b"] / "f.txt"), [dirs["a"]])) == []


def test_iter_files_with_allowed_single_file_inside(dirs):
    f = str(dirs["a"] / "f.txt")
    assert list(ingest.iter_files(f, [dirs["a"]])) == [f]


def test_iter_files_root_outside_allowed_yields_nothing(dirs):
    assert list(ingest.iter_files(str(dirs["evil"]), [dirs["a"]])) == []


def test_iter_files_empty_allowed_list_yields_nothing(dirs):
    """allowed=[] は None と違い全拒否(fail-closed)。"""
    assert list(ingest.iter_files(str(dirs["a"]), [])) == []
