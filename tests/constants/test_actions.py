"""Tests for action identifier constants module."""

import pytest

from sia_scraper.constants import (
    BACK_BTTN,
    CAMPUS_DD,
    CAMPUS_ELECTIVES_DD,
    CAREER_DD,
    COURSE_PAGE_LINK,
    FACULTY_CAREER_DD,
    FACULTY_DD,
    SELECT_ROW,
    SHOW_COURSES_BTTN,
    STUDY_LEVEL_DD,
    TIPOLOGY_DD,
)


@pytest.mark.unit
class TestActionIdentifiers:
    """Test action identifier constants."""

    def test_dropdown_identifiers_exist(self) -> None:
        """Test all dropdown identifiers are defined."""
        identifiers = [
            STUDY_LEVEL_DD,
            CAMPUS_DD,
            FACULTY_DD,
            CAREER_DD,
            TIPOLOGY_DD,
            FACULTY_CAREER_DD,
            CAMPUS_ELECTIVES_DD,
        ]
        for identifier in identifiers:
            assert isinstance(identifier, str)
            assert len(identifier) > 0

    def test_button_identifiers_exist(self) -> None:
        """Test button identifiers are defined."""
        assert isinstance(SHOW_COURSES_BTTN, str)
        assert isinstance(BACK_BTTN, str)
        assert len(SHOW_COURSES_BTTN) > 0
        assert len(BACK_BTTN) > 0

    def test_action_identifiers_exist(self) -> None:
        """Test action identifiers are defined."""
        assert isinstance(SELECT_ROW, str)
        assert isinstance(COURSE_PAGE_LINK, str)

    def test_action_names_consistency(self) -> None:
        """Test action identifier naming is consistent."""
        dropdown_actions = [
            STUDY_LEVEL_DD,
            CAMPUS_DD,
            FACULTY_DD,
            CAREER_DD,
            TIPOLOGY_DD,
            FACULTY_CAREER_DD,
            CAMPUS_ELECTIVES_DD,
        ]

        for action in dropdown_actions:
            assert action.endswith("_DD")
