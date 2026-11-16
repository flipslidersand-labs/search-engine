"""server.py / cli.py が create_embedder() 経由で EMBEDDING_URL を尊重することの回帰テスト。"""

import argparse

import pytest

from searchengine import cli, embedder, server


class _FakeLocal:
    """実モデルをロードしないローカル Embedder の代役。"""

    def __init__(self, *a, **k):
        pass


@pytest.fixture(autouse=True)
def _no_real_model(monkeypatch, tmp_path):
    monkeypatch.setattr(embedder, "Embedder", _FakeLocal)
    monkeypatch.setattr(server, "_DB_PATH", str(tmp_path / "t.db"))


def _server_embedder():
    return server._open_index(want_vector=True).embedder


def _cli_embedder(tmp_path):
    args = argparse.Namespace(db=str(tmp_path / "c.db"))
    return cli._make_index(args, want_vector=True).embedder


@pytest.mark.parametrize("which", ["server", "cli"])
def test_embedding_url_selects_fallback_with_remote(monkeypatch, tmp_path, which):
    monkeypatch.setenv("EMBEDDING_URL", "http://example.invalid:1")

    class _FakeRemote:
        dim = 4
        backend = "remote:fake"

        def __init__(self, *a, **k):
            pass

    # dim 取得失敗時はローカルに落ちる (#137) ため、到達可能なリモートを模す
    monkeypatch.setattr(embedder, "RemoteEmbedder", _FakeRemote)
    emb = _server_embedder() if which == "server" else _cli_embedder(tmp_path)
    assert isinstance(emb, embedder.FallbackEmbedder)


@pytest.mark.parametrize("which", ["server", "cli"])
def test_without_embedding_url_uses_local(monkeypatch, tmp_path, which):
    monkeypatch.delenv("EMBEDDING_URL", raising=False)
    emb = _server_embedder() if which == "server" else _cli_embedder(tmp_path)
    assert isinstance(emb, _FakeLocal)
