"""contextual.py のテスト（#82）。

Ollama への HTTP 呼び出しは unittest.mock.patch で差し替える。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from searchengine.chunker import Chunk
from searchengine.contextual import add_context, generate_context
from searchengine.llm import OllamaClient


def _mock_ollama_response(content: str) -> MagicMock:
    m = MagicMock()
    m.raise_for_status = MagicMock()
    m.json.return_value = {"message": {"content": content}}
    return m


def test_generate_context_returns_llm_output():
    with patch("httpx.post", return_value=_mock_ollama_response("  第2章の導入部分です  ")):
        result = generate_context("文書全体のテキスト", "チャンクのテキスト")
    assert result == "第2章の導入部分です"


def test_generate_context_returns_none_on_llm_failure():
    with patch("httpx.post", side_effect=httpx.ConnectError("接続失敗")):
        result = generate_context("doc", "chunk")
    assert result is None


def test_generate_context_returns_none_on_empty_response():
    with patch("httpx.post", return_value=_mock_ollama_response("   ")):
        result = generate_context("doc", "chunk")
    assert result is None


def test_add_context_prepends_prefix_to_each_chunk():
    chunks = [Chunk(index=0, text="最初のチャンク"), Chunk(index=1, text="次のチャンク")]
    with patch("httpx.post", return_value=_mock_ollama_response("位置づけの説明")):
        result = add_context("文書全体", chunks)

    assert len(result) == 2
    assert result[0].index == 0
    assert result[0].text == "位置づけの説明\n\n最初のチャンク"
    assert result[1].text == "位置づけの説明\n\n次のチャンク"


def test_add_context_falls_back_to_original_text_on_failure():
    chunks = [Chunk(index=0, text="元のテキスト")]
    with patch("httpx.post", side_effect=httpx.ConnectError("接続失敗")):
        result = add_context("文書全体", chunks)

    assert result[0].text == "元のテキスト"


def test_add_context_uses_provided_client():
    client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:7b")
    chunks = [Chunk(index=0, text="チャンク")]
    with patch("httpx.post", return_value=_mock_ollama_response("説明")) as mock_post:
        add_context("文書", chunks, client=client)
    assert mock_post.call_count == 1


@pytest.mark.parametrize("chunks", [[]])
def test_add_context_empty_chunk_list(chunks):
    with patch("httpx.post", return_value=_mock_ollama_response("説明")) as mock_post:
        result = add_context("文書", chunks)
    assert result == []
    mock_post.assert_not_called()
