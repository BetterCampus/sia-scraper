"""Tests for business logic constants module."""

import pytest

from sia_scraper.constants import (
    COURSE_CODE_COL,
    COURSE_NAME_COL,
    DROPDOWN_FIRST_OPTION_OFFSET,
    ELECTIVES_CAMPUS_INCREMENT,
    ELECTIVES_TYPOLOGY_INDEX,
    FACULTY_CAREER_DEFAULT_INDEX,
    GROUP_DURATION_INDEX,
    GROUP_FACULTY_INDEX,
    GROUP_SCHEDULE_TYPE_INDEX,
    GROUP_SCHEDULES_INDEX,
    GROUP_SPOTS_INDEX,
    GROUP_TEACHER_INDEX,
    MIN_CONDITION_DIVS,
    MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
    PREREQ_DIV_START,
    REQUIRED_CONDITION_HEADERS,
    TIPOLOGY_VALUE_INDEX,
)


@pytest.mark.unit
class TestBusinessConstants:
    """Test business logic constants."""

    def test_business_constants_are_integers(self) -> None:
        """Test that business constants are of expected types."""
        assert isinstance(ELECTIVES_CAMPUS_INCREMENT, int)
        assert isinstance(DROPDOWN_FIRST_OPTION_OFFSET, int)
        assert isinstance(COURSE_CODE_COL, int)
        assert isinstance(COURSE_NAME_COL, int)
        assert isinstance(GROUP_TEACHER_INDEX, int)
        assert isinstance(GROUP_FACULTY_INDEX, int)
        assert isinstance(GROUP_SCHEDULES_INDEX, int)
        assert isinstance(GROUP_DURATION_INDEX, int)
        assert isinstance(GROUP_SCHEDULE_TYPE_INDEX, int)
        assert isinstance(GROUP_SPOTS_INDEX, int)
        assert isinstance(MIN_GROUP_DATA_LENGTH_WITH_SPOTS, int)
        assert isinstance(MIN_CONDITION_DIVS, int)
        assert isinstance(PREREQ_DIV_START, int)
        assert isinstance(REQUIRED_CONDITION_HEADERS, int)
        assert isinstance(TIPOLOGY_VALUE_INDEX, int)

    def test_group_indices_are_valid(self) -> None:
        """Test that group indices form a valid sequence."""
        indices = [
            GROUP_TEACHER_INDEX,
            GROUP_FACULTY_INDEX,
            GROUP_SCHEDULES_INDEX,
            GROUP_DURATION_INDEX,
            GROUP_SCHEDULE_TYPE_INDEX,
            GROUP_SPOTS_INDEX,
        ]
        expected = [0, 1, 2, 3, 4, 5]
        assert indices == expected

    def test_min_group_data_length_with_spots(self) -> None:
        """Test MIN_GROUP_DATA_LENGTH_WITH_SPOTS is correctly calculated."""
        expected_indices = [0, 1, 2, 3, 4, 5]
        assert MIN_GROUP_DATA_LENGTH_WITH_SPOTS == len(expected_indices)
        assert MIN_GROUP_DATA_LENGTH_WITH_SPOTS == 6

    def test_electives_constants(self) -> None:
        """Test electives-related constants."""
        assert ELECTIVES_CAMPUS_INCREMENT == 40
        assert ELECTIVES_TYPOLOGY_INDEX == "7"
        assert FACULTY_CAREER_DEFAULT_INDEX == "0"

    def test_dropdown_offset(self) -> None:
        """Test dropdown first option offset."""
        assert DROPDOWN_FIRST_OPTION_OFFSET == 1

    def test_prerequisite_constants(self) -> None:
        """Test prerequisite-related constants."""
        assert MIN_CONDITION_DIVS == 5
        assert PREREQ_DIV_START == 6
        assert REQUIRED_CONDITION_HEADERS == 3
        assert TIPOLOGY_VALUE_INDEX == 2
