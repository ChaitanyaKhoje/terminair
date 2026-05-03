"""Shared logging helpers with opt-in debug output and basic redaction."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def _debug_enabled() -> bool:
    return os.environ.get("AIRTERM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_log_path() -> Path:
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        base = Path(xdg_state) / "airterm"
    else:
        base = Path.home() / ".local" / "state" / "airterm"
    base.mkdir(parents=True, exist_ok=True)
    return base / "debug.log"


def get_logger(name: str) -> logging.Logger:
    """Create or return a module logger.

    Logging is disabled by default and only enabled when AIRTERM_DEBUG is set.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.propagate = False
    if not _debug_enabled():
        logger.addHandler(logging.NullHandler())
        return logger

    try:
        fh = logging.FileHandler(_safe_log_path(), mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)
    except Exception:
        logger.addHandler(logging.NullHandler())

    return logger


def sanitize_error(value: str, limit: int = 120) -> str:
    """Best-effort sanitization for error text surfaced in the UI."""
    text = " ".join(value.split())
    for marker in ("Authorization", "Bearer ", "token=", "password="):
        idx = text.find(marker)
        if idx >= 0:
            text = text[:idx] + "[redacted]"
    return text[:limit]
