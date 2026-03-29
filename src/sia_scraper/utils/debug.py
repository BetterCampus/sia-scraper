"""Debug logging utilities for Oracle ADF state investigation."""

import logging
import os
from typing import Any

DEBUG_MODE: bool = os.environ.get("SIA_DEBUG", "0") == "1"
_LOGGER = logging.getLogger("sia_scraper.adf")


def debug_log(message: str, data: str | dict[str, Any] | None = None) -> None:
    """Log debug output when ``SIA_DEBUG=1`` is set."""
    if not DEBUG_MODE:
        return

    _LOGGER.debug("[ADF-DEBUG] %s", message)

    if not data:
        return

    if isinstance(data, dict):
        for key, value in data.items():
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            _LOGGER.debug("  %s: %s", key, value_str)
        return

    data_str = str(data)
    if len(data_str) > 200:
        data_str = data_str[:200] + "..."
    _LOGGER.debug("  Data: %s", data_str)
