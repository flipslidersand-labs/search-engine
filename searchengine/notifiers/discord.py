"""Discord webhook notifications for search engine indexing events."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class DiscordNotifier:
  """Send indexing events to Discord via webhook."""

  def __init__(self) -> None:
    """Initialize Discord notifier from environment variables."""
    self.completion_webhook = os.getenv("DISCORD_WEBHOOK_COMPLETION")
    self.error_webhook = os.getenv("DISCORD_WEBHOOK_ERRORS")

  def send_indexing_complete(
    self,
    doc_count: int,
    chunk_count: int,
    duration_seconds: float,
    tokenizer: str = "Unknown",
    has_vector: bool = False,
  ) -> bool:
    """Send notification when indexing completes.

    Args:
        doc_count: Number of documents indexed
        chunk_count: Number of chunks created
        duration_seconds: Total indexing duration
        tokenizer: Tokenizer backend used
        has_vector: Whether vector indexing was enabled

    Returns:
        True if notification sent successfully
    """
    if not self.completion_webhook:
      logger.debug("Discord completion webhook not configured")
      return False

    try:
      description = f"Indexed **{doc_count}** document(s) into **{chunk_count}** chunk(s)"
      backend = "hybrid" if has_vector else "keyword"

      embed = {
        "title": "Search Index Complete",
        "description": description,
        "color": 65280,  # Green
        "fields": [
          {"name": "Documents", "value": str(doc_count), "inline": True},
          {"name": "Chunks", "value": str(chunk_count), "inline": True},
          {"name": "Duration", "value": f"{duration_seconds:.2f}s", "inline": True},
          {"name": "Tokenizer", "value": tokenizer, "inline": True},
          {"name": "Search Mode", "value": backend, "inline": True},
        ],
        "timestamp": datetime.now(UTC).isoformat(),
      }

      return self._send_webhook(self.completion_webhook, {"embeds": [embed]})
    except Exception as e:
      logger.error(f"Failed to send indexing notification: {e}")
      return False

  def send_indexing_error(
    self,
    error_message: str,
    error_type: str | None = None,
    doc_path: str | None = None,
  ) -> bool:
    """Send notification when indexing fails.

    Args:
        error_message: Error message
        error_type: Error type (optional)
        doc_path: Path of document that failed (optional)

    Returns:
        True if notification sent successfully
    """
    if not self.error_webhook:
      logger.debug("Discord error webhook not configured")
      return False

    try:
      fields = [
        {"name": "Status", "value": "FAILED", "inline": True},
      ]

      if doc_path:
        fields.append({"name": "Document", "value": doc_path, "inline": False})

      if error_type:
        fields.append({"name": "Error Type", "value": error_type, "inline": True})

      embed = {
        "title": "Search Index Failed",
        "description": error_message,
        "color": 15158332,  # Red
        "fields": fields,
        "timestamp": datetime.now(UTC).isoformat(),
      }

      return self._send_webhook(self.error_webhook, {"embeds": [embed]})
    except Exception as e:
      logger.error(f"Failed to send error notification: {e}")
      return False

  def _send_webhook(self, webhook_url: str, payload: dict[str, Any]) -> bool:
    """Send payload to Discord webhook.

    Args:
        webhook_url: Discord webhook URL
        payload: JSON payload to send

    Returns:
        True if successful (HTTP 204)
    """
    try:
      data = json.dumps(payload).encode("utf-8")
      req = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
      )

      with urlopen(req, timeout=5) as response:
        if response.status == 204:
          logger.debug("Discord notification sent successfully")
          return True
        else:
          logger.error(f"Discord webhook returned {response.status}")
          return False
    except URLError as e:
      logger.error(f"Failed to connect to Discord: {e}")
      return False
    except Exception as e:
      logger.error(f"Unexpected error sending Discord notification: {e}")
      return False
