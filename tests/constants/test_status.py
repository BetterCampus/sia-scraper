"""Tests for SiaSessionStatus enum module."""

from enum import Enum

import pytest

from sia_scraper.constants import SiaSessionStatus


@pytest.mark.unit
class TestSiaSessionStatus:
    """Test SiaSessionStatus enumeration."""

    def test_session_status_is_enum(self) -> None:
        """Test SiaSessionStatus is an Enum class."""
        assert issubclass(SiaSessionStatus, Enum)

    def test_all_statuses_exist(self) -> None:
        """Test all expected session statuses are defined."""
        expected_statuses = [
            "NO_SESSION",
            "CAREER_NOT_SET",
            "ON_CAREER_PAGE",
            "ON_COURSE_PAGE",
        ]

        for status_name in expected_statuses:
            assert hasattr(SiaSessionStatus, status_name)

    def test_status_values(self) -> None:
        """Test status enum values match their names."""
        assert SiaSessionStatus.NO_SESSION.value == "NO_SESSION"
        assert SiaSessionStatus.CAREER_NOT_SET.value == "CAREER_NOT_SET"
        assert SiaSessionStatus.ON_CAREER_PAGE.value == "ON_CAREER_PAGE"
        assert SiaSessionStatus.ON_COURSE_PAGE.value == "ON_COURSE_PAGE"

    def test_status_uniqueness(self) -> None:
        """Test all status values are unique."""
        statuses = list(SiaSessionStatus)
        values = [s.value for s in statuses]
        assert len(values) == len(set(values))

    def test_status_count(self) -> None:
        """Test expected number of statuses."""
        assert len(list(SiaSessionStatus)) == 4

    def test_status_iteration(self) -> None:
        """Test iterating over status enum."""
        statuses = [status for status in SiaSessionStatus]
        assert len(statuses) == 4
        assert SiaSessionStatus.NO_SESSION in statuses
        assert SiaSessionStatus.CAREER_NOT_SET in statuses
        assert SiaSessionStatus.ON_CAREER_PAGE in statuses
        assert SiaSessionStatus.ON_COURSE_PAGE in statuses

    def test_status_string_representation(self) -> None:
        """Test string representation of statuses."""
        assert str(SiaSessionStatus.NO_SESSION) == "SiaSessionStatus.NO_SESSION"

    def test_status_comparison(self) -> None:
        """Test status enum comparison."""
        assert SiaSessionStatus.NO_SESSION == SiaSessionStatus.NO_SESSION
        assert SiaSessionStatus.NO_SESSION != SiaSessionStatus.CAREER_NOT_SET

    def test_status_from_name(self) -> None:
        """Test creating status from string name."""
        status = SiaSessionStatus["ON_CAREER_PAGE"]
        assert status == SiaSessionStatus.ON_CAREER_PAGE
        assert status.value == "ON_CAREER_PAGE"
