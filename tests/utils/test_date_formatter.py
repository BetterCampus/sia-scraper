"""Comprehensive test suite for date formatter module."""

import datetime

from sia_scraper.date_formatter import format_date


class TestDateFormatterBasicFunctionality:
    """Test basic formatting functionality of format_date."""

    def test_format_date_typical_datetime(self) -> None:
        dt = datetime.datetime(2024, 12, 25, 15, 30, 45, 123456)
        assert format_date(dt) == "2024-12-25 15:30"

    def test_format_date_ignores_seconds(self) -> None:
        dt = datetime.datetime(2024, 3, 25, 14, 20, 59)
        assert format_date(dt) == "2024-03-25 14:20"

    def test_format_date_ignores_microseconds(self) -> None:
        dt = datetime.datetime(2024, 3, 25, 14, 20, 30, 999999)
        assert format_date(dt) == "2024-03-25 14:20"


class TestDateFormatterPadding:
    """Test zero-padding functionality for single-digit date components."""

    def test_format_date_single_digit_month(self) -> None:
        dt = datetime.datetime(2024, 3, 15, 10, 30)
        assert format_date(dt) == "2024-03-15 10:30"

    def test_format_date_single_digit_day(self) -> None:
        dt = datetime.datetime(2024, 10, 5, 10, 30)
        assert format_date(dt) == "2024-10-05 10:30"

    def test_format_date_single_digit_hour(self) -> None:
        dt = datetime.datetime(2024, 10, 15, 9, 30)
        assert format_date(dt) == "2024-10-15 09:30"

    def test_format_date_single_digit_minute(self) -> None:
        dt = datetime.datetime(2024, 10, 15, 10, 7)
        assert format_date(dt) == "2024-10-15 10:07"

    def test_format_date_all_single_digits(self) -> None:
        dt = datetime.datetime(2024, 3, 5, 9, 7)
        assert format_date(dt) == "2024-03-05 09:07"


class TestDateFormatterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_format_date_midnight(self) -> None:
        dt = datetime.datetime(2024, 6, 15, 0, 0)
        assert format_date(dt) == "2024-06-15 00:00"

    def test_format_date_end_of_day(self) -> None:
        dt = datetime.datetime(2024, 6, 15, 23, 59)
        assert format_date(dt) == "2024-06-15 23:59"

    def test_format_date_leap_year_date(self) -> None:
        dt = datetime.datetime(2024, 2, 29, 12, 0)
        assert format_date(dt) == "2024-02-29 12:00"

    def test_format_date_first_day_of_year(self) -> None:
        dt = datetime.datetime(2024, 1, 1, 0, 0)
        assert format_date(dt) == "2024-01-01 00:00"

    def test_format_date_last_day_of_year(self) -> None:
        dt = datetime.datetime(2024, 12, 31, 23, 59)
        assert format_date(dt) == "2024-12-31 23:59"

    def test_format_date_year_boundary_9999(self) -> None:
        dt = datetime.datetime(9999, 12, 31, 23, 59)
        assert format_date(dt) == "9999-12-31 23:59"

    def test_format_date_year_with_three_digits(self) -> None:
        dt = datetime.datetime(999, 6, 15, 12, 30)
        assert format_date(dt) == "999-06-15 12:30"


class TestDateFormatterIntegration:
    """Test complete workflows and integration scenarios."""

    def test_single_call(self) -> None:
        dt = datetime.datetime(2024, 3, 25, 20, 15, 30)
        assert format_date(dt) == "2024-03-25 20:15"

    def test_multiple_calls_same_result(self) -> None:
        dt = datetime.datetime(2024, 7, 4, 16, 45)
        result1 = format_date(dt)
        result2 = format_date(dt)
        result3 = format_date(dt)
        assert result1 == result2 == result3 == "2024-07-04 16:45"

    def test_different_inputs_independent(self) -> None:
        dt1 = datetime.datetime(2024, 1, 1, 0, 0)
        dt2 = datetime.datetime(2024, 12, 31, 23, 59)

        assert format_date(dt1) == "2024-01-01 00:00"
        assert format_date(dt2) == "2024-12-31 23:59"
        assert format_date(dt1) == "2024-01-01 00:00"
