"""Comprehensive test suite for DateFormatter module.

This module contains pytest-based unit tests for the DateFormatter class,
which formats datetime objects into SIA-compatible string representations.
The tests cover all public and private methods, edge cases, and ensure
100% code coverage.

Tests are organized into logical groups:
- Basic formatting functionality
- Zero-padding for single-digit values
- Edge cases (boundaries, special dates)
- Private method testing
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
        """Test formatting a typical datetime with all double-digit components.

        Verifies that a datetime with double-digit month, day, hour, and minute
        is formatted correctly without any padding issues.
        """
        dt = datetime.datetime(2024, 12, 25, 15, 30, 45, 123456)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-12-25 15:30"

    def test_format_date_ignores_seconds(self) -> None:
        """Test that seconds are ignored in the formatted output.

        The SIA format only includes YYYY-MM-DD HH:MM, so seconds
        should be truncated without affecting the output.
        """
        dt = datetime.datetime(2024, 3, 25, 14, 20, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 14:20"

    def test_format_date_ignores_microseconds(self) -> None:
        """Test that microseconds are ignored in the formatted output.

        Microseconds should be completely ignored and not affect
        the formatting in any way.
        """
        dt = datetime.datetime(2024, 3, 25, 14, 20, 30, 999999)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 14:20"


class TestDateFormatterPadding:
    """Test zero-padding functionality for single-digit date components."""

    def test_format_date_single_digit_month(self) -> None:
        """Test formatting with a single-digit month (January-September).

        Verifies that months 1-9 are zero-padded to two digits.
        """
        dt = datetime.datetime(2024, 3, 15, 10, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-15 10:30"

    def test_format_date_single_digit_day(self) -> None:
        """Test formatting with a single-digit day (1-9).

        Verifies that days 1-9 are zero-padded to two digits.
        """
        dt = datetime.datetime(2024, 10, 5, 10, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-05 10:30"

    def test_format_date_single_digit_hour(self) -> None:
        """Test formatting with a single-digit hour (0-9).

        Verifies that hours 0-9 are zero-padded to two digits.
        """
        dt = datetime.datetime(2024, 10, 15, 9, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-15 09:30"

    def test_format_date_single_digit_minute(self) -> None:
        """Test formatting with a single-digit minute (0-9).

        Verifies that minutes 0-9 are zero-padded to two digits.
        """
        dt = datetime.datetime(2024, 10, 15, 10, 7)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-10-15 10:07"

    def test_format_date_all_single_digits(self) -> None:
        """Test formatting with all single-digit components.

        Verifies that when month, day, hour, and minute are all
        single digits, each is properly zero-padded.
        """
        dt = datetime.datetime(2024, 3, 5, 9, 7)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-05 09:07"


class TestDateFormatterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_format_date_midnight(self) -> None:
        """Test formatting at midnight (00:00).

        Verifies that hour 0 and minute 0 are both properly
        zero-padded.
        """
        dt = datetime.datetime(2024, 6, 15, 0, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-06-15 00:00"

    def test_format_date_end_of_day(self) -> None:
        """Test formatting at the last minute of the day (23:59).

        Verifies correct formatting of the maximum valid hour
        and minute values.
        """
        dt = datetime.datetime(2024, 6, 15, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-06-15 23:59"

    def test_format_date_leap_year_date(self) -> None:
        """Test formatting a leap year date (February 29).

        Verifies that leap year dates are handled correctly.
        """
        dt = datetime.datetime(2024, 2, 29, 12, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-02-29 12:00"

    def test_format_date_first_day_of_year(self) -> None:
        """Test formatting the first day of the year (January 1).

        Verifies correct handling of year boundary dates.
        """
        dt = datetime.datetime(2024, 1, 1, 0, 0)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-01-01 00:00"

    def test_format_date_last_day_of_year(self) -> None:
        """Test formatting the last day of the year (December 31).

        Verifies correct handling of year boundary dates.
        """
        dt = datetime.datetime(2024, 12, 31, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-12-31 23:59"

    def test_format_date_year_boundary_9999(self) -> None:
        """Test formatting with the maximum 4-digit year (9999).

        Verifies that the year 9999 is represented correctly
        without any truncation or padding issues.
        """
        dt = datetime.datetime(9999, 12, 31, 23, 59)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "9999-12-31 23:59"

    def test_format_date_year_with_three_digits(self) -> None:
        """Test formatting with a year less than 1000.

        Verifies that years with fewer than 4 digits are
        represented without zero-padding the year.
        """
        dt = datetime.datetime(999, 6, 15, 12, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "999-06-15 12:30"


class TestDateFormatterPrivateMethod:
    """Test the private __pad_to_two_digits static method."""

    def test_pad_to_two_digits_single_digit(self) -> None:
        """Test padding a single-digit number.

        Verifies that single-digit numbers (0-9) are
        zero-padded to two digits.
        """
        # Access the name-mangled private method
        result = DateFormatter._DateFormatter__pad_to_two_digits(5)  # type: ignore[attr-defined]
        assert result == "05"

    def test_pad_to_two_digits_double_digit(self) -> None:
        """Test padding a double-digit number.

        Verifies that double-digit numbers remain unchanged.
        """
        result = DateFormatter._DateFormatter__pad_to_two_digits(15)  # type: ignore[attr-defined]
        assert result == "15"

    def test_pad_to_two_digits_zero(self) -> None:
        """Test padding zero.

        Verifies that 0 is padded to '00'.
        """
        result = DateFormatter._DateFormatter__pad_to_two_digits(0)  # type: ignore[attr-defined]
        assert result == "00"

    def test_pad_to_two_digits_edge_single_digit(self) -> None:
        """Test padding the edge case of single-digit 9.

        Verifies that the highest single-digit number is
        properly padded.
        """
        result = DateFormatter._DateFormatter__pad_to_two_digits(9)  # type: ignore[attr-defined]
        assert result == "09"

    def test_pad_to_two_digits_edge_double_digit(self) -> None:
        """Test padding common edge values for time components.

        Verifies padding for 59 (max minutes/seconds) and 23 (max hours).
        """
        assert DateFormatter._DateFormatter__pad_to_two_digits(59) == "59"  # type: ignore[attr-defined]
        assert DateFormatter._DateFormatter__pad_to_two_digits(23) == "23"  # type: ignore[attr-defined]

    def test_pad_to_two_digits_three_digit(self) -> None:
        """Test padding a three-digit number.

        Verifies that numbers with more than two digits
        are returned as-is (no truncation).
        """
        result = DateFormatter._DateFormatter__pad_to_two_digits(123)  # type: ignore[attr-defined]
        assert result == "123"


class TestDateFormatterIntegration:
    """Test complete workflows and integration scenarios."""

    def test_initialization_and_formatting(self) -> None:
        """Test the complete workflow from initialization to formatting.

        Verifies that the DateFormatter can be initialized with a
        datetime object and successfully format it.
        """
        dt = datetime.datetime(2024, 3, 25, 20, 15, 30)
        formatter = DateFormatter(dt)
        result = formatter.format_date()
        assert result == "2024-03-25 20:15"

    def test_multiple_format_date_calls(self) -> None:
        """Test calling format_date() multiple times on the same instance.

        Verifies that the formatter is stateless after initialization
        and returns the same result on repeated calls.
        """
        dt = datetime.datetime(2024, 7, 4, 16, 45)
        formatter = DateFormatter(dt)
        result1 = formatter.format_date()
        result2 = formatter.format_date()
        result3 = formatter.format_date()
        assert result1 == result2 == result3 == "2024-07-04 16:45"

    def test_different_formatters_independent(self) -> None:
        """Test that multiple DateFormatter instances are independent.

        Verifies that creating multiple formatters with different
        datetimes produces correct independent results.
        """
        dt1 = datetime.datetime(2024, 1, 1, 0, 0)
        dt2 = datetime.datetime(2024, 12, 31, 23, 59)

        formatter1 = DateFormatter(dt1)
        formatter2 = DateFormatter(dt2)

        assert formatter1.format_date() == "2024-01-01 00:00"
        assert formatter2.format_date() == "2024-12-31 23:59"
        # Verify first formatter still works correctly
        assert formatter1.format_date() == "2024-01-01 00:00"
