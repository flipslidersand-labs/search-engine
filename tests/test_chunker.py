"""chunk_text のサイズ判定(estimate_tokens ベース)と改行保持の回帰テスト (#138)。"""

from searchengine.chunker import Chunk, chunk_text, estimate_tokens

CODE = "def foo(x):\n    if x:\n        return 1\n    return 0\n"


def test_long_japanese_paragraph_without_spaces_is_split():
    text = "検索エンジンの評価を行う。" * 200  # 空白なし・約 2400 字
    chunks = chunk_text(text, size=512, overlap=64)
    assert len(chunks) > 1
    assert all(estimate_tokens(c.text) <= 512 for c in chunks)
    assert all(isinstance(c, Chunk) for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_japanese_split_covers_whole_text():
    text = "".join(chr(0x3041 + (i % 80)) for i in range(2000))
    chunks = chunk_text(text, size=300, overlap=30)
    assert chunks[0].text.startswith(text[:10])
    assert chunks[-1].text.endswith(text[-10:])


def test_code_keeps_newlines_and_indent():
    chunks = chunk_text(CODE)
    assert len(chunks) == 1
    assert chunks[0].text == CODE.strip("\n")
    assert "\n        return 1\n" in chunks[0].text


def test_long_code_paragraph_split_keeps_lines():
    code = "".join(f"    x{i} = {i}\n" for i in range(400))
    chunks = chunk_text(code, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(estimate_tokens(c.text) <= 200 for c in chunks)
    assert all("\n" in c.text for c in chunks)
    # チャンク内部の行はインデントを保持する
    for c in chunks:
        for line in c.text.split("\n")[1:]:
            assert line.startswith("    x")


def test_paragraphs_merged_with_blank_line_preserved():
    chunks = chunk_text("first para\n\nsecond para")
    assert len(chunks) == 1
    assert chunks[0].text == "first para\n\nsecond para"


def test_empty_and_whitespace():
    assert chunk_text("") == []
    assert chunk_text("  \n\n  ") == []
