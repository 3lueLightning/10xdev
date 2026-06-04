"""The project logger. Import `logger` from here; never use print().

Wraps loguru behind this module so the backend can be swapped later (e.g. for
structlog) without touching call sites. Console format is colored with
timestamp, level, and module:function:line; JSON format (for cloud) emits the
same fields to stdout for the platform's log collector to ingest.
"""

from __future__ import annotations

import sys

from loguru import logger

from {{pkg}}.config import get_settings

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def _configure() -> None:
    settings = get_settings()
    logger.remove()
    if settings.log_format == "json":
        logger.add(sys.stdout, level=settings.log_level, serialize=True)
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format=_CONSOLE_FORMAT,
            colorize=True,
        )


_configure()

__all__ = ["logger"]
