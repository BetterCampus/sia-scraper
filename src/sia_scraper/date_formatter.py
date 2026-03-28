"""Datetime formatting utilities for SIA scraper.

This module provides utilities for converting Python datetime objects into
standardized string formats required by the SIA API and data pipeline.

## Example
    >>> from datetime import datetime
    >>> dt = datetime(2024, 3, 25, 20, 15, 30)
    >>> formatter = DateFormatter(dt)
    >>> formatter.format_date()
    '2024-03-25 20:15'
"""

import datetime


class DateFormatter:
    """Formats datetime objects into SIA-compatible string representations.

    This class provides a standardized way to convert Python datetime objects
    into the `YYYY-MM-DD HH:MM` format required by SIA API endpoints and
    database operations. The formatter is stateless after initialization and
    can be used for a single formatting operation.

    ## Attributes
        date (datetime.datetime): The datetime object to be formatted.

    ## Example
        >>> from datetime import datetime
        >>> dt = datetime(2024, 12, 25, 15, 30, 45)
        >>> formatter = DateFormatter(dt)
        >>> formatter.format_date()
        '2024-12-25 15:30'
    """

    def __init__(self, date: datetime.datetime) -> None:
        """Initialize formatter with a datetime object.

        ## Args
            date: The datetime object to format. Must be a valid datetime
                instance with year, month, day, hour, and minute attributes.

        ## Raises
            TypeError: If date is not a datetime.datetime instance.

        ## Example
            >>> from datetime import datetime
            >>> dt = datetime.now()
            >>> formatter = DateFormatter(dt)
        """
        self.date = date

    @staticmethod
    def _pad_to_two_digits(num: int) -> str:
        """Pad an integer to exactly 2 digits with leading zeros.

        This is a private helper method used internally to ensure consistent
        formatting of date/time components (month, day, hours, minutes).

        ## Args
            num: The integer value to pad. Typically a date/time component
                (1-31 for day, 0-59 for minutes, etc.).

        ## Returns
            Zero-padded string representation of exactly 2 characters.
            Single-digit numbers are prefixed with '0'.

        ## Example
            >>> DateFormatter._pad_to_two_digits(5)
            '05'
            >>> DateFormatter._pad_to_two_digits(15)
            '15'
        """
        return str(num).zfill(2)

    def format_date(self) -> str:
        """Format the stored datetime to ISO-like 'YYYY-MM-DD HH:MM' format.

        Converts the datetime object passed during initialization into a
        standardized string format suitable for SIA API requests and
        database operations. Seconds and microseconds are intentionally
        omitted to match SIA requirements.

        ## Returns
            Formatted datetime string in 'YYYY-MM-DD HH:MM' format.
            Components are zero-padded as needed. The year is always
            4 digits; all other components are 2 digits.

        ## Example
            >>> from datetime import datetime
            >>> dt = datetime(2024, 3, 5, 9, 7, 30)
            >>> formatter = DateFormatter(dt)
            >>> formatter.format_date()
            '2024-03-05 09:07'

        ## Note
            The formatter always returns a string in the expected format,
            regardless of the input datetime's precision. Fractional seconds
            and microseconds are truncated without rounding.
        """
        year = str(self.date.year)
        month = self._pad_to_two_digits(self.date.month)
        day = self._pad_to_two_digits(self.date.day)
        hours = self._pad_to_two_digits(self.date.hour)
        minutes = self._pad_to_two_digits(self.date.minute)

        return f"{year}-{month}-{day} {hours}:{minutes}"
