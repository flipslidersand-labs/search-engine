"""Index の接続 close 保証のテスト（Issue #126）。"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient  # pylint: disable=import-error
from mcp import types

from searchengine import mcp_server, server
from searchengine.index import Index


@pytest.fixture()
def closed_counter(monkeypatch: pytest.MonkeyPatch) -> dict:
    """生成された Index 数と close された数を数える。"""
    state = {"opened": 0, "closed": 0}
    orig_init = Index.__init__
    orig_close = Index.close

    def init(self, *a, **kw):
        state["opened"] += 1
        orig_init(self, *a, **kw)

    def close(self):
        state["closed"] += 1
        orig_close(self)

    monkeypatch.setattr(Index, "__init__", init)
    monkeypatch.setattr(Index, "close", close)
    return state


def _call_mcp(name: str, args: dict) -> types.CallToolResult:
    handler = mcp_server.create_server().get_request_handler("tools/call")
    params = types.CallToolRequestParams(name=name, arguments=args)
    return asyncio.run(handler.handler(None, params))


def test_index_context_manager_closes(tmp_path: Path):
    with Index(str(tmp_path / "t.db")) as idx:
        idx.stats()
    with pytest.raises(sqlite3.ProgrammingError):
        idx.stats()


def test_index_context_manager_closes_on_exception(tmp_path: Path):
    with pytest.raises(RuntimeError):
        with Index(str(tmp_path / "t.db")) as idx:
            raise RuntimeError("boom")
    with pytest.raises(sqlite3.ProgrammingError):
        idx.stats()


@pytest.fixture()
def mcp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(mcp_server, "_DB_PATH", str(tmp_path / "m.db"))
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(tmp_path))
    (tmp_path / "a.md").write_text("# Hello\n\nPython document.", encoding="utf-8")
    return tmp_path


def test_mcp_stats_closes(mcp_env, closed_counter):
    res = _call_mcp("stats", {})
    assert not res.is_error
    assert closed_counter == {"opened": 1, "closed": 1}


def test_mcp_search_keyword_closes(mcp_env, closed_counter):
    res = _call_mcp("search", {"query": "Python", "mode": "keyword"})
    assert not res.is_error
    assert closed_counter == {"opened": 1, "closed": 1}


def test_mcp_search_closes_when_parse_fails(mcp_env, closed_counter, monkeypatch):
    def boom(_q):
        raise ValueError("bad query")

    monkeypatch.setattr(mcp_server, "parse_query", boom)
    res = _call_mcp("search", {"query": "x", "mode": "keyword"})
    assert res.is_error
    assert "bad query" in json.loads(res.content[0].text)["error"]
    assert closed_counter["opened"] == closed_counter["closed"] == 1


def test_mcp_index_closes(mcp_env, closed_counter):
    res = _call_mcp("index", {"path": str(mcp_env)})
    assert not res.is_error
    assert closed_counter == {"opened": 1, "closed": 1}


def test_mcp_ask_closes(mcp_env, closed_counter, monkeypatch):
    class _Emb:
        backend = "stub"

    monkeypatch.setattr("searchengine.embedder.create_embedder", lambda: _Emb())

    def fail(*_a, **_kw):
        raise RuntimeError("no ollama")

    monkeypatch.setattr(mcp_server, "rag_ask", fail)
    res = _call_mcp("ask", {"question": "q"})
    assert res.is_error
    assert closed_counter["opened"] == closed_counter["closed"] == 1


@pytest.fixture()
def api_client(tmp_path: Path):
    server._set_db(str(tmp_path / "s.db"))
    yield TestClient(server.app)
    server._set_db("search.db")


def test_server_search_closes_when_parse_fails(api_client, closed_counter, monkeypatch):
    def boom(_q):
        raise ValueError("bad query")

    monkeypatch.setattr(server.query, "parse", boom)
    with pytest.raises(ValueError):
        api_client.get("/search", params={"q": "x", "mode": "keyword"})
    assert closed_counter["opened"] == closed_counter["closed"] == 1


def test_server_stats_and_search_close(api_client, closed_counter):
    assert api_client.get("/stats").status_code == 200
    assert api_client.get("/search", params={"q": "x", "mode": "keyword"}).status_code == 200
    assert closed_counter == {"opened": 2, "closed": 2}
