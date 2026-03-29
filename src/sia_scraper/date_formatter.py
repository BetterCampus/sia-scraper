"""Datetime formatting utilities for SIA scraper.

This module provides utilities for converting Python datetime objects into
standardized string formats required by the SIA API and data pipeline.
"""

from datetime import datetime

DATE_FORMAT = "%Y-%m-%d %H:%M"


def format_date(date: datetime) -> str:
    """Format datetime to ``YYYY-MM-DD HH:MM`` format.

    Args:
        date: The datetime object to format.

    Returns:
        Datetime formatted as ``YYYY-MM-DD HH:MM``.
    """
    return date.strftime(DATE_FORMAT)
