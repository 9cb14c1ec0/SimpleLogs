"""
SimpleLogs Python Client

Usage:
    from simplelogs import SimpleLogger

    logger = SimpleLogger("http://localhost", "your-api-key")
    logger.info("User logged in", {"user_id": 123})
    logger.error("Payment failed", {"order_id": 456, "amount": 99.99})
"""

import requests
from typing import Any
from datetime import datetime


class SimpleLogger:
    def __init__(self, base_url: str, api_key: str, source: str | None = None):
        self.url = f"{base_url}/api/v1/ingest"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self.source = source

    def _send(self, level: str, message: str, metadata: dict[str, Any] | None = None):
        payload = {
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if metadata:
            payload["metadata"] = metadata
        if self.source:
            payload["source"] = self.source

        try:
            requests.post(self.url, json=payload, headers=self.headers, timeout=5)
        except Exception:
            pass  # Fire and forget

    def debug(self, message: str, metadata: dict[str, Any] | None = None):
        self._send("debug", message, metadata)

    def info(self, message: str, metadata: dict[str, Any] | None = None):
        self._send("info", message, metadata)

    def warn(self, message: str, metadata: dict[str, Any] | None = None):
        self._send("warn", message, metadata)

    def error(self, message: str, metadata: dict[str, Any] | None = None):
        self._send("error", message, metadata)

    def fatal(self, message: str, metadata: dict[str, Any] | None = None):
        self._send("fatal", message, metadata)

    def batch(self, logs: list[dict[str, Any]]):
        """Send multiple logs at once."""
        try:
            requests.post(
                f"{self.url}/batch",
                json={"logs": logs},
                headers=self.headers,
                timeout=10,
            )
        except Exception:
            pass
