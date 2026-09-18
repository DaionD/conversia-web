"""Logging setup for AMRAS: console output plus rotating audit files under /logs.

Two file streams are kept separate:
- amras.log        general application/system logs.
- execution.log     order execution telemetry (slippage, fees, latency).
"""
from __future__ import annotations

import logging
import logging.handlers

from config.settings import LOG_DIR, settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("amras")
    if root.handlers:
        return  # already configured

    root.setLevel(settings.log_level.upper())
    root.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    app_file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "amras.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    app_file_handler.setFormatter(formatter)
    root.addHandler(app_file_handler)

    execution_logger = logging.getLogger("amras.execution")
    execution_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "execution.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    execution_handler.setFormatter(formatter)
    execution_logger.addHandler(execution_handler)
    execution_logger.propagate = True
