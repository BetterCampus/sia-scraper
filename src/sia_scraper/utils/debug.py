"""Debug logging utilities for Oracle ADF state investigation.

This module provides structured logging using loguru with automatic:
- Log rotation (10 MB per file)
- Retention (7 days)
- Console output when SIA_DEBUG=1
- File output to logs/ directory
"""

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

DEBUG_MODE: bool = os.environ.get("SIA_DEBUG", "0") == "1"

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

if DEBUG_MODE:
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

logger.add(
    LOG_DIR / "sia_scraper_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    serialize=False,
)

logger.add(
    LOG_DIR / "sia_scraper_errors_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="14 days",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    serialize=False,
)


def debug_log(message: str, data: str | dict[str, Any] | None = None) -> None:
    """Log debug output when ``SIA_DEBUG=1`` is set.

    This function maintains backward compatibility with the old debug_log interface
    while leveraging loguru's structured logging capabilities.

    ## Args
        message: The log message
        data: Optional additional data to log (dict for structured logging)

    ## Example
        debug_log("ViewState sync completed", {"length": 500, "status": "success"})
        debug_log("Request failed")  # Logs without additional data
    """
    if not DEBUG_MODE:
        return

    if data is None:
        logger.debug(message)
    elif isinstance(data, dict):
        logger.debug(message, **data)
    else:
        logger.debug(message, extra={"data": str(data)})


def info_log(message: str, data: dict[str, Any] | None = None) -> None:
    """Log informational messages to file.

    ## Args
        message: The log message
        data: Optional additional data to log
    """
    if data is None:
        logger.info(message)
    elif isinstance(data, dict):
        logger.info(message, **data)
    else:
        logger.info(message, extra={"data": str(data)})


def error_log(message: str, data: dict[str, Any] | None = None) -> None:
    """Log error messages to both file and error log.

    ## Args
        message: The error message
        data: Optional additional data to log
    """
    if data is None:
        logger.error(message)
    elif isinstance(data, dict):
        logger.error(message, **data)
    else:
        logger.error(message, extra={"data": str(data)})
