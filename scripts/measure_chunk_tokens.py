#!/usr/bin/env python3
"""チャンクの e5 token 長分布を計測する (#95)。

`chunker.DEFAULT_SIZE` は「空白区切りの語数」であり tokens ではない。
multilingual-e5 の上限 512 tokens（`passage: ` と特殊トークン分を含む）を超えると
embedding-svc は末尾を黙って切り詰めるため、実コーパスでの超過率を測る。

使い方:
  python3 scripts/measure_chunk_tokens.py docs/ sample_docs/
  python3 scripts/measure_chunk_tokens.py ~/notes --size 200 --prefix-tokens 100

--prefix-tokens は contextual prefix が占める tokens の想定値（最悪ケース見積もり）。
tokenizer はローカルの HF キャッシュを使用（`transformers` 必須、ネットワーク不要）。
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from searchengine import chunker

MODEL = "intfloat/multilingual-e5-base"
MAX_SEQ = 512


def _iter_files(paths: list[str]):
    for p in map(Path, paths):
        if p.is_file():
            yield p
        else:
            yield from sorted(p.rglob("*.md"))


def _percentile(sorted_vals: list[int], q: float) -> int:
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * q))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="計測対象の .md ファイル/ディレクトリ")
    ap.add_argument("--size", type=int, default=chunker.DEFAULT_SIZE)
    ap.add_argument("--overlap", type=int, default=chunker.DEFAULT_OVERLAP)
    ap.add_argument("--prefix-tokens", type=int, default=100)
    ap.add_argument(
        "--guard",
        action="store_true",
        help="Index と同じ split_to_token_budget を適用して計測（ベクトル索引時の実挙動）",
    )
    args = ap.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)

    lens: list[int] = []
    files = 0
    for f in _iter_files(args.paths):
        text = f.read_text(encoding="utf-8", errors="ignore")
        files += 1
        chunks = chunker.chunk_text(text, size=args.size, overlap=args.overlap)
        if args.guard:
            budget = chunker.EMBED_TOKEN_BUDGET - args.prefix_tokens
            chunks = chunker.split_to_token_budget(chunks, budget)
        for c in chunks:
            # e5 は index 時に "passage: " が付く。特殊トークン(<s>,</s>)込みで数える
            lens.append(len(tok(f"passage: {c.text}", truncation=False)["input_ids"]))

    if not lens:
        print("チャンクが0件です", file=sys.stderr)
        return 1

    lens.sort()
    over = sum(n > MAX_SEQ for n in lens)
    over_prefix = sum(n + args.prefix_tokens > MAX_SEQ for n in lens)
    n = len(lens)
    print(f"files={files} chunks={n} size={args.size} overlap={args.overlap}")
    print(
        f"tokens: mean={statistics.mean(lens):.0f} p50={_percentile(lens, .5)} "
        f"p95={_percentile(lens, .95)} max={lens[-1]}"
    )
    print(f">{MAX_SEQ} tokens (prefixなし):            {over}/{n} = {over / n:.1%}")
    print(
        f">{MAX_SEQ} tokens (prefix {args.prefix_tokens} tokens想定): "
        f"{over_prefix}/{n} = {over_prefix / n:.1%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
