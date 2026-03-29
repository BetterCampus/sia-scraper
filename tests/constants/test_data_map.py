"""Tests for DATA_MAP and DROPDOWNS constants module."""

import pytest

from sia_scraper.constants import (
    BACK_BTTN,
    BACK_BTTN_ID,
    BTTN_EVENT_VALUE,
    CAMPUS_DD,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD,
    CAREER_DD_ID,
    COURSE_PAGE_LINK,
    DATA_MAP,
    DROPDOWN_EVENT_VALUE,
    DROPDOWNS,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD,
    FACULTY_DD_ID,
    SELECT_ROW,
    SELECT_ROW_EVENT_VALUE,
    SELECT_ROW_ID,
    SHOW_COURSES_BTTN,
    SHOW_CURSES_BTTN_ID,
    STUDY_LEVEL_DD,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD,
    TIPOLOGY_DD_ID,
)


@pytest.mark.unit
class TestDerivedIdentifiers:
    """Test derived identifier lists."""

    def test_dropdowns_list(self) -> None:
        """Test DROPDOWNS list contains content region suffixes."""
        assert isinstance(DROPDOWNS, list)
        assert len(DROPDOWNS) == 4

        expected_dropdowns = [
            f"{STUDY_LEVEL_DD_ID}::content",
            f"{CAMPUS_DD_ID}::content",
            f"{FACULTY_DD_ID}::content",
            f"{CAREER_DD_ID}::content",
        ]
        assert DROPDOWNS == expected_dropdowns

    def test_dropdowns_have_content_suffix(self) -> None:
        """Test all dropdown IDs have ::content suffix."""
        for dropdown in DROPDOWNS:
            assert dropdown.endswith("::content")
            assert "::" in dropdown


@pytest.mark.unit
class TestDataMap:
    """Test DATA_MAP action-to-component mapping."""

    def test_data_map_structure(self) -> None:
        """Test DATA_MAP is a dictionary with proper structure."""
        assert isinstance(DATA_MAP, dict)
        assert len(DATA_MAP) > 0

        for _key, value in DATA_MAP.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)
            assert isinstance(value[1], str)

    def test_data_map_dropdown_actions(self) -> None:
        """Test dropdown actions are mapped correctly."""
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
            assert action in DATA_MAP
            component_id, event = DATA_MAP[action]
            assert event == DROPDOWN_EVENT_VALUE

    def test_data_map_button_actions(self) -> None:
        """Test button actions are mapped correctly."""
        button_actions = [SHOW_COURSES_BTTN, BACK_BTTN, COURSE_PAGE_LINK]

        for action in button_actions:
            assert action in DATA_MAP
            component_id, event = DATA_MAP[action]
            assert event == BTTN_EVENT_VALUE

    def test_data_map_select_row_action(self) -> None:
        """Test SELECT_ROW action is mapped correctly."""
        assert SELECT_ROW in DATA_MAP
        component_id, event = DATA_MAP[SELECT_ROW]
        assert event == SELECT_ROW_EVENT_VALUE

    @pytest.mark.parametrize(
        "action,expected_id",
        [
            (STUDY_LEVEL_DD, STUDY_LEVEL_DD_ID),
            (CAMPUS_DD, CAMPUS_DD_ID),
            (FACULTY_DD, FACULTY_DD_ID),
            (CAREER_DD, CAREER_DD_ID),
            (TIPOLOGY_DD, TIPOLOGY_DD_ID),
            (SHOW_COURSES_BTTN, SHOW_CURSES_BTTN_ID),
            (FACULTY_CAREER_DD, FACULTY_CAREER_DD_ID),
            (CAMPUS_ELECTIVES_DD, CAMPUS_ELECTIVES_DD_ID),
            (SELECT_ROW, SELECT_ROW_ID),
            (COURSE_PAGE_LINK, SELECT_ROW_ID),
            (BACK_BTTN, BACK_BTTN_ID),
        ],
    )
    def test_data_map_component_ids(self, action: str, expected_id: str) -> None:
        """Test DATA_MAP maps actions to correct component IDs."""
        component_id, _ = DATA_MAP[action]
        assert component_id == expected_id

    def test_data_map_completeness(self) -> None:
        """Test DATA_MAP contains all defined actions."""
        expected_actions = [
            STUDY_LEVEL_DD,
            CAMPUS_DD,
            FACULTY_DD,
            CAREER_DD,
            TIPOLOGY_DD,
            SHOW_COURSES_BTTN,
            FACULTY_CAREER_DD,
            CAMPUS_ELECTIVES_DD,
            SELECT_ROW,
            COURSE_PAGE_LINK,
            BACK_BTTN,
        ]

        for action in expected_actions:
            assert action in DATA_MAP, f"Action {action} not in DATA_MAP"

    def test_dropdown_ids_match_data_map(self) -> None:
        """Test all dropdown component IDs appear in DATA_MAP."""
        dropdown_ids = [
            STUDY_LEVEL_DD_ID,
            CAMPUS_DD_ID,
            FACULTY_DD_ID,
            CAREER_DD_ID,
            TIPOLOGY_DD_ID,
            FACULTY_CAREER_DD_ID,
            CAMPUS_ELECTIVES_DD_ID,
        ]

        data_map_component_ids = [comp_id for comp_id, _ in DATA_MAP.values()]

        for dd_id in dropdown_ids:
            assert dd_id in data_map_component_ids

    def test_button_ids_match_data_map(self) -> None:
        """Test all button component IDs appear in DATA_MAP."""
        button_ids = [SHOW_CURSES_BTTN_ID, BACK_BTTN_ID]

        data_map_component_ids = [comp_id for comp_id, _ in DATA_MAP.values()]

        for btn_id in button_ids:
            assert btn_id in data_map_component_ids
