"""Tests for Discord notifier."""

import os
from unittest.mock import MagicMock, patch

import pytest

from searchengine.notifiers.discord import DiscordNotifier


class TestDiscordNotifier:
  """Test suite for DiscordNotifier."""

  def test_init_with_env_vars(self):
    """Test initialization with environment variables."""
    with patch.dict(
      os.environ,
      {
        "DISCORD_WEBHOOK_COMPLETION": "https://discord.com/api/webhooks/123/abc",
        "DISCORD_WEBHOOK_ERRORS": "https://discord.com/api/webhooks/456/def",
      },
    ):
      notifier = DiscordNotifier()
      assert notifier.completion_webhook == "https://discord.com/api/webhooks/123/abc"
      assert notifier.error_webhook == "https://discord.com/api/webhooks/456/def"

  def test_init_without_env_vars(self):
    """Test initialization without environment variables."""
    with patch.dict(os.environ, {}, clear=True):
      notifier = DiscordNotifier()
      assert notifier.completion_webhook is None
      assert notifier.error_webhook is None

  @patch("searchengine.notifiers.discord.urlopen")
  def test_send_indexing_complete_success(self, mock_urlopen):
    """Test successful indexing completion notification."""
    mock_response = MagicMock()
    mock_response.status = 204
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch.dict(
      os.environ,
      {"DISCORD_WEBHOOK_COMPLETION": "https://discord.com/api/webhooks/123/abc"},
    ):
      notifier = DiscordNotifier()
      result = notifier.send_indexing_complete(
        doc_count=10,
        chunk_count=50,
        duration_seconds=30.5,
        tokenizer="cl100k_base",
        has_vector=True,
      )
      assert result is True
      assert mock_urlopen.called

  @patch("searchengine.notifiers.discord.urlopen")
  def test_send_indexing_complete_webhook_not_configured(self, mock_urlopen):
    """Test indexing complete when webhook not configured."""
    with patch.dict(os.environ, {}, clear=True):
      notifier = DiscordNotifier()
      result = notifier.send_indexing_complete(
        doc_count=10,
        chunk_count=50,
        duration_seconds=30.5,
      )
      assert result is False
      assert not mock_urlopen.called

  @patch("searchengine.notifiers.discord.urlopen")
  def test_send_indexing_error_success(self, mock_urlopen):
    """Test successful error notification."""
    mock_response = MagicMock()
    mock_response.status = 204
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch.dict(
      os.environ,
      {"DISCORD_WEBHOOK_ERRORS": "https://discord.com/api/webhooks/456/def"},
    ):
      notifier = DiscordNotifier()
      result = notifier.send_indexing_error(
        error_message="Failed to parse document",
        error_type="ParseError",
        doc_path="/data/file.pdf",
      )
      assert result is True
      assert mock_urlopen.called

  @patch("searchengine.notifiers.discord.urlopen")
  def test_send_webhook_network_error(self, mock_urlopen):
    """Test webhook send with network error."""
    from urllib.error import URLError

    mock_urlopen.side_effect = URLError("Connection refused")

    with patch.dict(
      os.environ,
      {"DISCORD_WEBHOOK_COMPLETION": "https://discord.com/api/webhooks/123/abc"},
    ):
      notifier = DiscordNotifier()
      result = notifier.send_indexing_complete(doc_count=1, chunk_count=1, duration_seconds=1)
      assert result is False
