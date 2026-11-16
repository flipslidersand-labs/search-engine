"""schema_gen.cli の引数解析テスト (tmp のみ使用)。"""

import pytest

from searchengine.schema_gen import cli


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "sample-data.csv"
    p.write_text("id,name\n1,a\n2,b\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("flag", ["--out", "--sheet", "--table", "--format", "--credentials"])
def test_trailing_flag_without_value_is_argparse_error(csv_file, flag):
    with pytest.raises(SystemExit) as e:
        cli.main([str(csv_file), flag])
    assert e.value.code == 2


def test_invalid_format_is_argparse_error(csv_file):
    with pytest.raises(SystemExit) as e:
        cli.main([str(csv_file), "--format", "bogus"])
    assert e.value.code == 2


def test_no_file_and_no_sheets_exits_1(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--er"])
    assert e.value.code == 1
    assert "--sheets" in capsys.readouterr().err


def test_help_prints_doc(capsys):
    cli.main(["--help"])
    assert "schema-gen CLI" in capsys.readouterr().out


def test_sql_only_stdout(csv_file, capsys):
    cli.main([str(csv_file), "--format", "sql", "--table", "t1"])
    out = capsys.readouterr().out
    assert "t1" in out


def test_out_dir_writes_files(csv_file, tmp_path):
    out = tmp_path / "o"
    cli.main([str(csv_file), "--out", str(out), "--er"])
    assert (out / "sample-data-report.md").exists()
    assert (out / "sample-data-schema.sql").exists()
    assert (out / "sample-data-er.md").exists()
