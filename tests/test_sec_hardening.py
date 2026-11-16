"""#167 セキュリティ硬化の回帰テスト。"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from searchengine.schema_gen.analyzer import analyze
from searchengine.schema_gen.er import render_sql_with_fk
from searchengine.schema_gen.reporter import report_sql
from searchengine.schema_gen.store import SchemaStore

EVIL = 'a" TEXT); DROP TABLE x; --'


def _cols():
    return analyze([{EVIL: "1", "id": "1"}, {EVIL: "2", "id": "2"}])


def test_report_sql_escapes_identifiers():
    sql = report_sql('t" (a); DROP TABLE x; --', _cols())
    assert 'CREATE TABLE "t"" (a); DROP TABLE x; --"' in sql
    assert '"a"" TEXT); DROP TABLE x; --"' in sql
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE x (k)")
    con.executescript(sql)
    assert con.execute("SELECT name FROM sqlite_master WHERE name='x'").fetchone()


def test_er_sql_escapes_identifiers():
    sql = render_sql_with_fk("tbl", _cols(), [])
    assert 'CREATE TABLE "tbl"' in sql
    assert '"a"" TEXT); DROP TABLE x; --"' in sql


def test_deploy_excludes_env():
    text = (Path(__file__).parent.parent / "deploy.sh").read_text()
    assert "--exclude='.env'" in text


@pytest.fixture
def store(tmp_path):
    s = SchemaStore(tmp_path / "t.db")
    s.save("orders", "o.csv", analyze([{"order_id": "1", "total": "5"}]), 1, sql="")
    return s


@pytest.mark.parametrize("q", ['"', "a AND", "(", "col:", "a OR OR b", "*", "NEAR("])
def test_store_search_special_chars_do_not_raise(store, q):
    assert isinstance(store.search_columns(q), list)
    assert isinstance(store.search_columns(q, field="col_name"), list)


def test_store_search_still_matches(store):
    assert store.search_columns("order_id", field="col_name")
    assert store.search_columns("order_id")


def test_api_search_bad_syntax_not_500(tmp_path):
    from fastapi.testclient import TestClient

    import searchengine.schema_gen.api as api_mod
    from searchengine.server import app

    s = SchemaStore(tmp_path / "t.db")
    with patch.object(api_mod, "_store", return_value=s):
        r = TestClient(app, raise_server_exceptions=False).get("/schema/search", params={"q": '"'})
    assert r.status_code == 200


def test_mcp_unexpected_error_is_generic(tmp_path, monkeypatch):
    import json

    import asyncio

    from mcp import types

    from searchengine import mcp_server

    def boom(_q):
        raise RuntimeError("connect http://internal:11434 failed")

    monkeypatch.setattr(mcp_server, "parse_query", boom)
    monkeypatch.setattr(mcp_server, "_DB_PATH", str(tmp_path / "m.db"))
    handler = mcp_server.create_server().get_request_handler("tools/call")
    params = types.CallToolRequestParams(name="search", arguments={"query": "x", "mode": "keyword"})
    res = asyncio.run(handler.handler(None, params))
    assert res.is_error
    assert "11434" not in res.content[0].text
    assert json.loads(res.content[0].text)["error"] == "internal error"
