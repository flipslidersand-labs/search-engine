#!/usr/bin/env python3
"""
schema-gen CLI — CSV/Excel/Google Sheets 構造解析 → 要件定義・DBスキーマ生成

使い方:
  python -m searchengine.schema_gen.cli <file>          # CSV/Excel
  python -m searchengine.schema_gen.cli --sheets <url>  # Google Sheets

オプション:
  --sheet <name>        Excel/Sheets シート名（省略時は最初のシート）
  --sheets <url|id>     Google Sheets URL またはスプレッドシート ID
  --credentials <path>  認証ファイル（service_account.json or client_secret.json）
  --table <name>        SQL テーブル名（省略時はファイル名から推定）
  --out <dir>           出力ディレクトリ（省略時は標準出力）
  --format md|sql|both  出力形式（デフォルト: both）
  --er                  ER図（Mermaid）+ 正規化提案を追加出力
  --req                 要件定義書テンプレートを出力（--out 指定時は .md + .xlsx）
"""

import argparse
import sys
from pathlib import Path

from searchengine.schema_gen.analyzer import analyze
from searchengine.schema_gen.ingest import load_file, load_sheets
from searchengine.schema_gen.reporter import report_er, report_markdown, report_sql
from searchengine.schema_gen.requirements_doc import (
    render_requirements_md,
    render_requirements_xlsx,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="schema-gen", add_help=False)
    p.add_argument("file", nargs="?")
    p.add_argument("--sheet")
    p.add_argument("--sheets")
    p.add_argument("--credentials")
    p.add_argument("--table")
    p.add_argument("--out")
    p.add_argument("--format", choices=("md", "sql", "both"), default="both")
    p.add_argument("--er", action="store_true")
    p.add_argument("--req", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    ns = _build_parser().parse_args(args)
    sheet = ns.sheet
    out_dir = Path(ns.out) if ns.out else None
    fmt = ns.format
    sheets_url = ns.sheets
    credentials = ns.credentials
    include_er = ns.er
    include_req = ns.req

    if sheets_url:
        rows, source_id = load_sheets(sheets_url, sheet, credentials)
        stem = source_id[:20]
        filename = f"sheets:{source_id[:12]}…"
    else:
        if not ns.file:
            print("ERROR: ファイルパスまたは --sheets を指定してください", file=sys.stderr)
            sys.exit(1)
        filepath = ns.file
        rows, filename = load_file(filepath, sheet)
        stem = Path(filepath).stem

    table_name = ns.table or stem.replace(" ", "_").replace("-", "_")

    if not rows:
        print("ERROR: データが空です", file=sys.stderr)
        sys.exit(1)

    columns = analyze(rows)
    row_count = len(rows)
    md = report_markdown(filename, columns, row_count) if fmt in ("md", "both") else None
    sql = report_sql(table_name, columns) if fmt in ("sql", "both") else None
    er = report_er(table_name, columns) if include_er else None
    req_md = (
        render_requirements_md(filename, table_name, columns, row_count) if include_req else None
    )

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        if md:
            (out_dir / f"{stem}-report.md").write_text(md, encoding="utf-8")
            print(f"  → {out_dir}/{stem}-report.md")
        if sql:
            (out_dir / f"{stem}-schema.sql").write_text(sql, encoding="utf-8")
            print(f"  → {out_dir}/{stem}-schema.sql")
        if er:
            (out_dir / f"{stem}-er.md").write_text(er, encoding="utf-8")
            print(f"  → {out_dir}/{stem}-er.md")
        if req_md:
            (out_dir / f"{stem}-requirements.md").write_text(req_md, encoding="utf-8")
            print(f"  → {out_dir}/{stem}-requirements.md")
            try:
                render_requirements_xlsx(
                    filename, table_name, columns, row_count, out_dir / f"{stem}-requirements.xlsx"
                )
                print(f"  → {out_dir}/{stem}-requirements.xlsx")
            except ImportError:
                print("  ⚠ Excel 出力スキップ (pip install openpyxl)")
    else:
        if md:
            print(md)
        if sql:
            print("\n---\n")
            print(sql)
        if er:
            print("\n---\n")
            print(er)
        if req_md:
            print("\n---\n")
            print(req_md)


if __name__ == "__main__":
    main()
