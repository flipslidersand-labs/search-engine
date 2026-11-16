"""cli.py の cmd_index / cmd_search / cmd_stats / main の挙動テスト (#172)。

DB・文書は tmp_path のみ。--vector 系は実 embedder に行かないよう create_embedder を
決定的なスタブへ差し替える（ネットワーク・Ollama・モデルロードに触れない）。
"""

from __future__ import annotations

import numpy as np
import pytest

from searchengine import cli


class _StubEmbedder:
    backend = "stub"
    dim = 16

    def encode(self, texts, mode="index"):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for ch in t:
                out[i, ord(ch) % self.dim] += 1.0
            n = np.linalg.norm(out[i])
            if n:
                out[i] /= n
        return out


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    # 既定 DB (search.db) が cwd に作られても tmp_path 内に収める
    monkeypatch.chdir(tmp_path)
    for k in ("EMBEDDING_URL", "SEARCH_ENGINE_CONTEXTUAL_PREFIX"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr("searchengine.embedder.create_embedder", lambda: _StubEmbedder())


@pytest.fixture()
def docs(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "ml.md").write_text("機械学習モデルの学習手順について説明する。", encoding="utf-8")
    (d / "cook.txt").write_text("カレーの作り方と材料の一覧。", encoding="utf-8")
    (d / "app.py").write_text(
        "def train_model():\n    return 'machine learning'\n", encoding="utf-8"
    )
    return d


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "cli.db")


def _run(capsys, *argv):
    rc = cli.main(list(argv))
    return rc, capsys.readouterr().out


def test_index_search_stats_flow(capsys, docs, db):
    rc, out = _run(capsys, "index", str(docs), "--db", db)
    assert rc == 0
    assert "indexed 3 file(s)" in out
    assert "embedder=" not in out
    assert "documents=3" in out

    rc, out = _run(capsys, "search", "機械学習", "--db", db)
    assert rc == 0
    assert out.startswith("mode=keyword fts=")
    assert "ml.md" in out
    assert "cook.txt" not in out
    assert "(chunk 0)" in out

    rc, out = _run(capsys, "stats", "--db", db)
    assert rc == 0
    assert out.startswith("documents=3 chunks=")
    assert "tokenizer=" in out


def test_index_empty_directory(capsys, tmp_path, db):
    empty = tmp_path / "empty"
    empty.mkdir()
    rc, out = _run(capsys, "index", str(empty), "--db", db)
    assert rc == 0
    assert "indexed 0 file(s)" in out
    assert "documents=0 chunks=0" in out


def test_index_single_file(capsys, docs, db):
    rc, out = _run(capsys, "index", str(docs / "ml.md"), "--db", db)
    assert rc == 0
    assert "indexed 1 file(s)" in out
    assert "documents=1" in out


def test_index_skips_unsupported_extension(capsys, tmp_path, db):
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.bin").write_bytes(b"\x00\x01")
    rc, out = _run(capsys, "index", str(d), "--db", db)
    assert rc == 0
    assert "indexed 0 file(s)" in out


def test_index_with_vector_reports_embedder(capsys, docs, db):
    rc, out = _run(capsys, "index", str(docs), "--db", db, "--vector")
    assert rc == 0
    assert "indexed 3 file(s)" in out
    assert "embedder=stub" in out


def test_reindex_is_idempotent(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db)
    rc, out = _run(capsys, "index", str(docs), "--db", db)
    assert rc == 0
    assert "documents=3" in out


def test_search_keyword_no_results(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db)
    rc, out = _run(capsys, "search", "存在しない単語zzzqqq", "--db", db)
    assert rc == 0
    assert out.startswith("(no results) mode=keyword")


def test_search_on_empty_db_no_results(capsys, db):
    rc, out = _run(capsys, "search", "機械学習", "--db", db)
    assert rc == 0
    assert out.startswith("(no results)")


def test_search_limit_n(capsys, tmp_path, db):
    d = tmp_path / "many"
    d.mkdir()
    for i in range(4):
        (d / f"f{i}.md").write_text(f"共通キーワード banana {i}", encoding="utf-8")
    _run(capsys, "index", str(d), "--db", db)
    rc, out = _run(capsys, "search", "banana", "-n", "2", "--db", db)
    assert rc == 0
    assert " 1. [" in out and " 2. [" in out and " 3. [" not in out


def test_search_filters_type_and_path(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db)
    rc, out = _run(capsys, "search", "model type:code", "--db", db)
    assert rc == 0
    assert "filters={'type': 'code'}" in out
    assert "app.py" in out
    assert "ml.md" not in out

    rc, out = _run(capsys, "search", "機械学習 path:cook", "--db", db)
    assert rc == 0
    assert "filters={'path': 'cook'}" in out
    # path フィルタで絞られ ml.md は出ない
    assert "ml.md" not in out


def test_search_filter_only_mismatch_no_results(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db)
    rc, out = _run(capsys, "search", "機械学習 type:code", "--db", db)
    assert rc == 0
    assert out.startswith("(no results)")
    assert "filters={'type': 'code'}" in out


def test_search_vector_mode(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db, "--vector")
    rc, out = _run(capsys, "search", "機械学習モデル", "--mode", "vector", "--db", db)
    assert rc == 0
    assert out.startswith("mode=vector")
    assert " 1. [" in out
    assert "(chunk " in out


def test_search_hybrid_mode(capsys, docs, db):
    _run(capsys, "index", str(docs), "--db", db, "--vector")
    rc, out = _run(capsys, "search", "機械学習", "--mode", "hybrid", "--db", db)
    assert rc == 0
    assert out.startswith("mode=hybrid")
    assert "ml.md" in out


def test_search_vector_mode_no_results_on_empty_db(capsys, db):
    rc, out = _run(capsys, "search", "何か", "--mode", "vector", "--db", db)
    assert rc == 0
    assert out.startswith("(no results) mode=vector")


def test_search_invalid_mode_exits(capsys, db):
    with pytest.raises(SystemExit) as e:
        cli.main(["search", "x", "--mode", "bogus", "--db", db])
    assert e.value.code == 2


def test_search_vector_mode_on_keyword_only_db_no_results(docs, db, capsys):
    # --vector 無しで索引した DB にベクトルは無いので vector 検索は 0 件
    cli.main(["index", str(docs), "--db", db])
    rc = cli.main(["search", "機械学習", "--mode", "vector", "--db", db])
    assert rc == 0
    assert "(no results)" in capsys.readouterr().out


def _db_position_roundtrip(capsys, docs, db, position):
    def argv(*rest):
        return ["--db", db, *rest] if position == "before" else [*rest, "--db", db]

    assert cli.main(argv("index", str(docs))) == 0
    capsys.readouterr()
    assert cli.main(argv("search", "機械学習")) == 0
    assert "ml.md" in capsys.readouterr().out
    assert cli.main(argv("stats")) == 0
    assert "documents=3" in capsys.readouterr().out


def test_db_option_after_subcommand(capsys, docs, tmp_path):
    db = tmp_path / "after.db"
    _db_position_roundtrip(capsys, docs, str(db), "after")
    assert db.exists()
    assert not (tmp_path / "search.db").exists()


@pytest.mark.xfail(
    strict=True,
    reason="既知: サブパーサの default=search.db が親パーサの --db を上書きし、"
    "サブコマンド前置の --db が無視される (server 側のみ #169 で修正済み)",
)
def test_db_option_before_subcommand(capsys, docs, tmp_path):
    db = tmp_path / "before.db"
    _db_position_roundtrip(capsys, docs, str(db), "before")
    assert db.exists()
    assert not (tmp_path / "search.db").exists()


def test_default_db_is_search_db_in_cwd(capsys, docs, tmp_path):
    cli.main(["index", str(docs)])
    capsys.readouterr()
    assert (tmp_path / "search.db").exists()


def test_stats_empty_db(capsys, db):
    rc, out = _run(capsys, "stats", "--db", db)
    assert rc == 0
    assert out.startswith("documents=0 chunks=0 tokenizer=")


def test_no_subcommand_exits(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2
