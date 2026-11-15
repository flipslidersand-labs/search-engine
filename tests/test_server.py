"""FastAPI サーバーのエンドポイントテスト（Phase 3）。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient  # pylint: disable=import-error

from searchengine import hybrid, server
from searchengine.index import Index


@pytest.fixture()
def tmp_db(tmp_path: Path):
    db = str(tmp_path / "test.db")
    server._set_db(db)
    yield db
    server._set_db("search.db")


@pytest.fixture()
def client(tmp_db):
    return TestClient(server.app)


@pytest.fixture()
def sample_dir(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "a.txt").write_text(
        "機械学習はデータからパターンを学習する分野である。", encoding="utf-8"
    )
    (tmp_path / "b.txt").write_text(
        "ベクトル検索は意味的類似性に基づく検索手法である。", encoding="utf-8"
    )
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(tmp_path))
    return tmp_path


# ── /health ───────────────────────────────────────────────────────────────────


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── / (Web UI) ────────────────────────────────────────────────────────────────


def test_web_ui(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SearchEngine" in r.text


# ── /stats（空DB） ────────────────────────────────────────────────────────────


def test_stats_empty(client):
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["documents"] == 0
    assert data["chunks"] == 0
    assert "tokenizer" in data


# ── /index ────────────────────────────────────────────────────────────────────


def test_index(client, sample_dir):
    r = client.post("/index", json={"path": str(sample_dir)})
    assert r.status_code == 200
    data = r.json()
    assert data["indexed"] == 2
    assert data["documents"] == 2
    assert data["chunks"] >= 2


def test_index_continues_after_one_file_fails(client, sample_dir, monkeypatch):
    # 1ファイルの失敗でバッチ全体を止めず、失敗件数を返す (#113)
    from searchengine import ingest

    real = ingest.read_text

    def flaky(path: str) -> str:
        if path.endswith("a.txt"):
            raise OSError("読めない")
        return real(path)

    monkeypatch.setattr(ingest, "read_text", flaky)
    r = client.post("/index", json={"path": str(sample_dir)})
    assert r.status_code == 200
    data = r.json()
    assert data["indexed"] == 1
    assert data["failed"] == 1
    assert data["documents"] == 1


def test_http_api_ignores_db_param(client, sample_dir, tmp_db, tmp_path):
    # 任意パスの DB を開ける db パラメータは HTTP API から廃止 (#91)。
    # 渡されても無視され、指定パスにファイルは作られない。
    other = tmp_path / "elsewhere" / "other.db"
    other.parent.mkdir()
    client.post("/index", json={"path": str(sample_dir), "db": str(other)})
    client.get("/search", params={"q": "機械学習", "db": str(other)})
    r = client.get("/stats", params={"db": str(other)})
    assert not other.exists()
    assert r.json()["db"] == tmp_db
    assert r.json()["documents"] == 2  # 既定 DB に取り込まれている


def test_index_nonexistent_path(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(tmp_path))
    r = client.post("/index", json={"path": str(tmp_path / "nonexistent_xyz")})
    assert r.status_code == 400
    assert "パスが存在しません" in r.json()["detail"]


# ── /search ───────────────────────────────────────────────────────────────────


def test_search_after_index(client, sample_dir):
    client.post("/index", json={"path": str(sample_dir)})
    r = client.get("/search", params={"q": "機械学習", "mode": "keyword"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["results"][0]["rank"] == 1
    assert "snippet" in data["results"][0]


def test_search_empty_query(client):
    r = client.get("/search", params={"q": "  "})
    assert r.status_code == 400


def test_search_no_results(client):
    r = client.get("/search", params={"q": "全くヒットしないはずのワード12345xyz"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_search_n_limit(client, sample_dir):
    client.post("/index", json={"path": str(sample_dir)})
    r = client.get("/search", params={"q": "検索", "n": 1})
    assert r.status_code == 200
    assert len(r.json()["results"]) <= 1


def test_stats_after_index(client, sample_dir):
    client.post("/index", json={"path": str(sample_dir)})
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["documents"] == 2


# ── /index セキュリティ: パストラバーサル対策 (#32) ──────────────────────────


def test_index_path_traversal_no_allowed_dirs(client, monkeypatch):
    monkeypatch.delenv("ALLOWED_INDEX_DIRS", raising=False)
    r = client.post("/index", json={"path": "/etc/passwd"})
    assert r.status_code == 403
    assert "ALLOWED_INDEX_DIRS" in r.json()["detail"]


def test_index_path_traversal_outside_allowed(client, tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(allowed))
    r = client.post("/index", json={"path": "/etc/passwd"})
    assert r.status_code == 403
    assert "許可されていないパス" in r.json()["detail"]


def test_index_path_traversal_symlink_escape(client, tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(allowed))
    # allowed/../../../etc/passwd のような相対パス
    evil = str(allowed) + "/../../../etc/passwd"
    r = client.post("/index", json={"path": evil})
    assert r.status_code == 403


def test_index_path_within_allowed(client, tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "doc.txt").write_text("test content", encoding="utf-8")
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(allowed))
    r = client.post("/index", json={"path": str(allowed)})
    assert r.status_code == 200
    assert r.json()["indexed"] == 1


def test_index_multiple_allowed_dirs(client, tmp_path, monkeypatch):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_b / "doc.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", f"{dir_a}:{dir_b}")
    r = client.post("/index", json={"path": str(dir_b)})
    assert r.status_code == 200


# ── API 認証: X-API-Key ヘッダー (#33) ───────────────────────────────────────


def test_api_key_not_set_allows_all(client, sample_dir, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = client.get("/search", params={"q": "test"})
    assert r.status_code == 200


def test_api_key_unset_fails_closed(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("ALLOW_NO_AUTH", raising=False)
    r = client.get("/search", params={"q": "test"})
    assert r.status_code == 401


def test_api_key_empty_fails_closed(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.delenv("ALLOW_NO_AUTH", raising=False)
    r = client.get("/stats", headers={"X-API-Key": ""})
    assert r.status_code == 401


def test_api_key_unset_allow_no_auth_flag(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NO_AUTH", "1")
    r = client.get("/stats")
    assert r.status_code == 200


def test_api_key_set_ignores_allow_no_auth(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    monkeypatch.setenv("ALLOW_NO_AUTH", "1")
    r = client.get("/stats", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_api_key_non_ascii_and_length_mismatch(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    for bad in ("s", "secret123-longer", "秘密キー"):
        r = client.get("/stats", headers={"X-API-Key": bad.encode("utf-8")})
        assert r.status_code == 401


def test_api_key_valid(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    r = client.get("/search", params={"q": "test"}, headers={"X-API-Key": "secret123"})
    assert r.status_code == 200


def test_api_key_invalid(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    r = client.get("/search", params={"q": "test"}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    assert "Invalid API Key" in r.json()["detail"]


def test_api_key_missing_header(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    r = client.get("/search", params={"q": "test"})
    assert r.status_code == 401


def test_health_no_api_key_required(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    r = client.get("/health")
    assert r.status_code == 200


def test_api_key_index_protected(client, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(tmp_path))
    r = client.post("/index", json={"path": str(tmp_path)})
    assert r.status_code == 401


def test_api_key_stats_protected(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    r = client.get("/stats")
    assert r.status_code == 401


def test_index_skips_symlink_pointing_outside_allowed(client, tmp_path, monkeypatch):
    """許可ディレクトリ内の symlink が範囲外ファイルを指す場合は取り込まない(#119)。"""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("TOPSECRETWORD", encoding="utf-8")
    (allowed / "ok.txt").write_text("normal content", encoding="utf-8")
    (allowed / "x.txt").symlink_to(outside / "secret.txt")
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(allowed))
    r = client.post("/index", json={"path": str(allowed)})
    assert r.status_code == 200
    assert r.json()["indexed"] == 1
    r = client.get("/search", params={"q": "TOPSECRETWORD"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_validate_index_path_rejects_empty_entries(tmp_path, monkeypatch):
    """ALLOWED_INDEX_DIRS=':' のような空指定は未設定扱いで拒否される。"""
    from searchengine.security import PathNotAllowedError, validate_index_path

    monkeypatch.setenv("ALLOWED_INDEX_DIRS", ":")
    with pytest.raises(PathNotAllowedError, match="未設定"):
        validate_index_path(str(tmp_path))


def test_search_nugget_uses_full_chunk_text(client, tmp_path, monkeypatch):
    """関連文がチャンク末尾にあっても原文から抽出され、マーカーが混入しない (#134)。"""
    filler = " ".join(f"Filler sentence number {i} about nothing." for i in range(30))
    (tmp_path / "long.txt").write_text(
        f"Alpha overview starts here. {filler} The zanzibar protocol requires quorum.",
        encoding="utf-8",
    )
    monkeypatch.setenv("ALLOWED_INDEX_DIRS", str(tmp_path))
    client.post("/index", json={"path": str(tmp_path)})

    def fts_only(idx, parsed, limit=10):
        return [hybrid.Fused(hit=h, rrf=h.score) for h in idx.search(parsed.fts, limit=limit)]

    monkeypatch.setattr(server.hybrid, "search", fts_only)
    monkeypatch.setattr(server, "_open_index", lambda want_vector=False: Index(server._DB_PATH))
    r = client.get("/search", params={"q": "zanzibar", "mode": "nugget", "nuggets_per_chunk": 1})
    assert r.status_code == 200
    snippet = r.json()["results"][0]["snippet"]
    assert "zanzibar protocol requires quorum" in snippet
    assert "[" not in snippet and "]" not in snippet


# ── /ask top_k 検証 (#133) ────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [0, -1, 21])
def test_ask_top_k_out_of_range_422(client, bad):
    r = client.post("/ask", json={"question": "q", "top_k": bad})
    assert r.status_code == 422
