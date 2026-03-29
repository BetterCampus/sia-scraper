"""Tests for ADF component ID constants module."""

import pytest

from sia_scraper.constants import (
    BACK_BTTN_ID,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD_ID,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD_ID,
    SELECT_ROW_ID,
    SHOW_COURSES_BTTN_ID,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD_ID,
)


@pytest.mark.unit
class TestAdfIdsComponentIds:
    """Test Oracle ADF component ID constants."""

    @pytest.mark.parametrize(
        "component_id,expected_prefix",
        [
            (STUDY_LEVEL_DD_ID, "pt1:r1:0:soc"),
            (CAMPUS_DD_ID, "pt1:r1:0:soc"),
            (FACULTY_DD_ID, "pt1:r1:0:soc"),
            (CAREER_DD_ID, "pt1:r1:0:soc"),
            (TIPOLOGY_DD_ID, "pt1:r1:0:soc"),
            (FACULTY_CAREER_DD_ID, "pt1:r1:0:soc"),
            (CAMPUS_ELECTIVES_DD_ID, "pt1:r1:0:soc"),
        ],
    )
    def test_dropdown_component_ids(self, component_id: str, expected_prefix: str) -> None:
        """Test that dropdown component IDs follow Oracle ADF pattern.

        Verifies all dropdown component IDs start with the expected
        Oracle ADF namespace prefix for single-selection components.
        """
        assert component_id.startswith(expected_prefix)
        assert isinstance(component_id, str)

    def test_button_component_ids(self) -> None:
        """Test that button component IDs follow Oracle ADF pattern.

        Verifies button component IDs use the correct Oracle ADF
        command button (cb) namespace and row positioning.
        """
        assert SHOW_COURSES_BTTN_ID.startswith("pt1:r1:0:cb")
        assert BACK_BTTN_ID.startswith("pt1:r1:1:cb")

    def test_table_component_id(self) -> None:
        """Test table component ID structure.

        Verifies the table row selection component ID follows
        Oracle ADF table (t) namespace conventions.
        """
        assert SELECT_ROW_ID.startswith("pt1:r1:0:t")

    def test_component_ids_are_unique(self) -> None:
        """Test that all component IDs are unique.

        Verifies no duplicate component IDs exist across all
        dropdown, button, and action components to prevent
        conflicts in the Oracle ADF component tree.
        """
        component_ids = [
            STUDY_LEVEL_DD_ID,
            CAMPUS_DD_ID,
            FACULTY_DD_ID,
            CAREER_DD_ID,
            TIPOLOGY_DD_ID,
            SHOW_COURSES_BTTN_ID,
            FACULTY_CAREER_DD_ID,
            CAMPUS_ELECTIVES_DD_ID,
            SELECT_ROW_ID,
            BACK_BTTN_ID,
        ]
        assert len(component_ids) == len(set(component_ids))
