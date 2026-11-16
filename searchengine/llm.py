"""Ollama LLM クライアント。

POST /api/chat を使い、非ストリーミングで応答を返す。
OLLAMA_URL 環境変数でベース URL を設定する（デフォルト: http://localhost:11434）。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

from .errors import SearchEngineError

_DEFAULT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_DEFAULT_MODEL = "qwen2.5:7b"
_TIMEOUT = 120.0


class LLMError(SearchEngineError):
    """LLM バックエンド呼び出しの失敗(HTTP 層・レスポンス不正を包む)。"""


def describe_error(e: BaseException) -> str:
    """str(e) が空でも原因が分かるよう型名を補う。"""
    msg = str(e)
    return f"{type(e).__name__}: {msg}" if msg else type(e).__name__


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResult:
    content: str
    model: str
    latency_ms: int


class OllamaClient:
    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[Message]) -> LLMResult:
        """メッセージリストを送信して応答テキストを返す。"""
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        t0 = time.monotonic()
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(describe_error(e)) from e
        latency_ms = int((time.monotonic() - t0) * 1000)
        try:
            content: str = resp.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as e:
            raise LLMError(f"不正なレスポンス: {describe_error(e)}") from e
        return LLMResult(content=content, model=self.model, latency_ms=latency_ms)
