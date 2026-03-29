"""Datetime formatting utilities for SIA scraper.

This module provides utilities for converting Python datetime objects into
standardized string formats required by the SIA API and data pipeline.
"""

from datetime import datetime

DATE_FORMAT = "%Y-%m-%d %H:%M"


class DateFormatter:
    """Formats datetime objects into SIA-compatible string representations.

    Converts Python datetime objects into the 'YYYY-MM-DD HH:MM' format
    required by SIA API endpoints and database operations.

    ## Example
        >>> formatter = DateFormatter(datetime(2024, 3, 25, 20, 15))
        >>> formatter.format_date()
        '2024-03-25 20:15'
    """

    def __init__(self, date: datetime) -> None:
        """Initialize formatter with a datetime object.

        ## Args
            date: The datetime object to format.
        """
        self.date = date

    def format_date(self) -> str:
        """Format datetime to 'YYYY-MM-DD HH:MM' format."""
        return self.date.strftime(DATE_FORMAT)
