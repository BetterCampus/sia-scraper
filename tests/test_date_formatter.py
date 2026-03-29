"""Comprehensive test suite for DateFormatter module.

This module contains pytest-based unit tests for the DateFormatter class,
which formats datetime objects into SIA-compatible string representations.

Tests are organized into logical groups:
- Basic formatting functionality
- Zero-padding for single-digit values
- Edge cases (boundaries, special dates)
- Integration workflows

Example:
    Run all tests with coverage::

        pytest tests/test_date_formatter.py --cov=src/sia_scraper/date_formatter
"""

import datetime

from sia_scraper.date_formatter import DateFormatter


class TestDateFormatterBasicFunctionality:
    """Test basic formatting functionality of DateFormatter."""

    def test_format_date_typical_datetime(self) -> None:
        """Test formatting a typical datetime with all double-digit components."""
        dt = datetime.datetime(2024, 12, 25, 15, 30, 45, 123456)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-12-25 15:30"

    def test_format_date_ignores_seconds(self) -> None:
        """Test that seconds are ignored in the formatted output."""
        dt = datetime.datetime(2024, 3, 25, 14, 20, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 14:20"

    def test_format_date_ignores_microseconds(self) -> None:
        """Test that microseconds are ignored in the formatted output."""
        dt = datetime.datetime(2024, 3, 25, 14, 20, 30, 999999)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 14:20"


class TestDateFormatterPadding:
    """Test zero-padding functionality for single-digit date components."""

    def test_format_date_single_digit_month(self) -> None:
        """Test formatting with a single-digit month (January-September)."""
        dt = datetime.datetime(2024, 3, 15, 10, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-15 10:30"

    def test_format_date_single_digit_day(self) -> None:
        """Test formatting with a single-digit day (1-9)."""
        dt = datetime.datetime(2024, 10, 5, 10, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-05 10:30"

    def test_format_date_single_digit_hour(self) -> None:
        """Test formatting with a single-digit hour (0-9)."""
        dt = datetime.datetime(2024, 10, 15, 9, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-15 09:30"

    def test_format_date_single_digit_minute(self) -> None:
        """Test formatting with a single-digit minute (0-9)."""
        dt = datetime.datetime(2024, 10, 15, 10, 7)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-15 10:07"

    def test_format_date_all_single_digits(self) -> None:
        """Test formatting with all single-digit components."""
        dt = datetime.datetime(2024, 3, 5, 9, 7)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-05 09:07"


class TestDateFormatterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_format_date_midnight(self) -> None:
        """Test formatting at midnight (00:00)."""
        dt = datetime.datetime(2024, 6, 15, 0, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-06-15 00:00"

    def test_format_date_end_of_day(self) -> None:
        """Test formatting at the last minute of the day (23:59)."""
        dt = datetime.datetime(2024, 6, 15, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-06-15 23:59"

    def test_format_date_leap_year_date(self) -> None:
        """Test formatting a leap year date (February 29)."""
        dt = datetime.datetime(2024, 2, 29, 12, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-02-29 12:00"

    def test_format_date_first_day_of_year(self) -> None:
        """Test formatting the first day of the year (January 1)."""
        dt = datetime.datetime(2024, 1, 1, 0, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-01-01 00:00"

    def test_format_date_last_day_of_year(self) -> None:
        """Test formatting the last day of the year (December 31)."""
        dt = datetime.datetime(2024, 12, 31, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-12-31 23:59"

    def test_format_date_year_boundary_9999(self) -> None:
        """Test formatting with the maximum 4-digit year (9999)."""
        dt = datetime.datetime(9999, 12, 31, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "9999-12-31 23:59"

    def test_format_date_year_with_three_digits(self) -> None:
        """Test formatting with a year less than 1000."""
        dt = datetime.datetime(999, 6, 15, 12, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "999-06-15 12:30"


class TestDateFormatterIntegration:
    """Test complete workflows and integration scenarios."""

    def test_initialization_and_formatting(self) -> None:
        """Test the complete workflow from initialization to formatting."""
        dt = datetime.datetime(2024, 3, 25, 20, 15, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 20:15"

    def test_multiple_format_date_calls(self) -> None:
        """Test calling format_date() multiple times on the same instance."""
        dt = datetime.datetime(2024, 7, 4, 16, 45)
        formatter = DateFormatter(dt)
        result1 = formatter.format_date()
        result2 = formatter.format_date()
        result3 = formatter.format_date()
        assert result1 == result2 == result3 == "2024-07-04 16:45"

    def test_different_formatters_independent(self) -> None:
        """Test that multiple DateFormatter instances are independent."""
        dt1 = datetime.datetime(2024, 1, 1, 0, 0)
        dt2 = datetime.datetime(2024, 12, 31, 23, 59)

        formatter1 = DateFormatter(dt1)
        formatter2 = DateFormatter(dt2)

        assert formatter1.format_date() == "2024-01-01 00:00"
        assert formatter2.format_date() == "2024-12-31 23:59"
        assert formatter1.format_date() == "2024-01-01 00:00"
