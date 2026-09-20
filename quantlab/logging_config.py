"""Standard library logging. Credentials are never logged."""

from __future__ import annotations

import logging
import os


_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    resolved = (level or os.environ.get("QUANTLAB_LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
