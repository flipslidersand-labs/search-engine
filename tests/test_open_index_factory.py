"""#140: server / mcp_server / cli が共通ファクトリで同じ設定の Index を作る回帰テスト。"""

from __future__ import annotations

import argparse

import pytest

from searchengine import cli, config, mcp_server, server


@pytest.mark.parametrize(
    "val,expected", [("1", True), ("true", True), ("YES", True), ("", False), ("0", False)]
)
def test_contextual_prefix_env_parsing(monkeypatch, val, expected):
    monkeypatch.setenv("SEARCH_ENGINE_CONTEXTUAL_PREFIX", val)
    assert config.contextual_prefix_enabled() is expected


def test_open_index_honors_prefix_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SEARCH_ENGINE_CONTEXTUAL_PREFIX", "1")
    with config.open_index(str(tmp_path / "a.db")) as idx:
        assert idx.use_contextual_prefix is True
    monkeypatch.delenv("SEARCH_ENGINE_CONTEXTUAL_PREFIX")
    with config.open_index(str(tmp_path / "b.db")) as idx:
        assert idx.use_contextual_prefix is False


def test_all_entrypoints_share_prefix_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("SEARCH_ENGINE_CONTEXTUAL_PREFIX", "true")
    db = str(tmp_path / "t.db")
    monkeypatch.setattr(server, "_DB_PATH", db)
    monkeypatch.setattr(mcp_server, "_DB_PATH", db)
    with server._open_index() as a, mcp_server._open_index() as b:
        assert a.use_contextual_prefix is True
        assert b.use_contextual_prefix is True
    c = cli._make_index(argparse.Namespace(db=db), want_vector=False)
    try:
        assert c.use_contextual_prefix is True
    finally:
        c.close()
