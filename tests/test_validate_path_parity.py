"""server.py と schema_gen/api.py のパス検証が同じ判定になること(#170)。"""

import pytest
from fastapi import HTTPException

from searchengine import server
from searchengine.schema_gen import api


def _result(fn, path):
    try:
        fn(path)
    except HTTPException as exc:
        return exc.status_code, exc.detail
    return None


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    (allowed / "a.csv").write_text("x")
    (outside / "b.csv").write_text("x")
    (allowed / "link").symlink_to(outside)
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(allowed))
    return allowed, outside


def _paths(allowed, outside):
    return [
        str(allowed / "a.csv"),
        str(outside / "b.csv"),
        str(allowed / ".." / "outside" / "b.csv"),
        str(allowed / "sub" / ".." / "a.csv"),
        str(allowed / "link" / "b.csv"),
        "",
    ]


def test_same_decision_when_set(dirs):
    allowed, outside = dirs
    for p in _paths(allowed, outside):
        assert _result(api._validate_path, p) == _result(server._validate_path, p), p
    assert _result(api._validate_path, str(allowed / "a.csv")) is None
    assert _result(api._validate_path, str(outside / "b.csv"))[0] == 403
    assert _result(api._validate_path, str(allowed / "link" / "b.csv"))[0] == 403
    assert _result(api._validate_path, str(allowed / ".." / "outside" / "b.csv"))[0] == 403


def test_same_decision_when_unset(dirs, monkeypatch):
    allowed, _ = dirs
    monkeypatch.delenv("ALLOWED_INDEX_DIRS")
    p = str(allowed / "a.csv")
    assert _result(api._validate_path, p) == _result(server._validate_path, p)
    assert _result(api._validate_path, p)[0] == 403


def test_same_decision_when_empty_entries(dirs, monkeypatch):
    allowed, _ = dirs
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", f":{allowed}: ")
    p = str(allowed / "a.csv")
    assert _result(api._validate_path, p) == _result(server._validate_path, p) is None
