"""
logger.py
---------
Central logging setup. Every module imports `get_logger(__name__)`
instead of configuring logging itself.

Rules:
- Never log secrets (API keys, passwords, tokens).
- Logs go to logs/shadow.log AND stdout.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from config import LOGS_DIR

_LOG_FILE = LOGS_DIR / "shadow.log"
_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger("shadow")
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"shadow.{name}")


_SENSITIVE_KEYS = {"api_key", "password", "token", "secret"}


def redact(data: dict) -> dict:
    """Return a copy of `data` with sensitive-looking keys masked, for safe logging."""
    out = {}
    for k, v in data.items():
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out
