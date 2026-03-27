"""Comprehensive test suite for SIA Constants module.

This module contains pytest-based unit tests for the constants defined in
sia_scraper.constants, including configuration values, action identifiers,
component IDs, event values, and the SiaSessionStatus enum. Tests verify
that all constants are properly defined and maintain expected values.

Tests are organized into logical groups:
- Basic constant values (timeout, URLs, IDs)
- Action identifiers (dropdowns, buttons)
- Component IDs and their structure
- Event values and XML formatting
- Dropdown list configuration
- DATA_MAP action-to-component mapping
- SIA HTTP headers
- SiaSessionStatus enum

Example:
    Run all tests with coverage::

        pytest tests/test_constants.py --cov=sia_scraper.constants
"""

import pytest

from src.sia_scraper.constants import (
    ADF_ADS_PAGE_ID,
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
    DEFAULT_TIMEOUT,
    DROPDOWN_EVENT_VALUE,
    DROPDOWNS,
    ELECTIVES_CAMPUS_INCREMENT,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD,
    FACULTY_DD_ID,
    SELECT_ROW,
    SELECT_ROW_EVENT_VALUE,
    SELECT_ROW_ID,
    SHOW_COURSES_BTTN,
    SHOW_CURSES_BTTN_ID,
    SIA_BASE_URL,
    SIA_HEADERS,
    STUDY_LEVEL_DD,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD,
    TIPOLOGY_DD_ID,
    SiaSessionStatus,
)


@pytest.mark.unit
class TestConstants:
    """Test basic constant values."""

    def test_default_timeout(self) -> None:
        """Test that DEFAULT_TIMEOUT is set to expected value.

        Verifies that the default request timeout for SIA sessions
        is configured to 15 seconds and stored as an integer type.
        """
        assert DEFAULT_TIMEOUT == 15
        assert isinstance(DEFAULT_TIMEOUT, int)

    def test_sia_base_url(self) -> None:
        """Test that SIA_BASE_URL points to the correct endpoint.

        Verifies the base URL for SIA's public service catalog page,
        ensuring it uses HTTPS and points to the correct JSF endpoint.
        """
        assert (
            SIA_BASE_URL
            == "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf"
        )
        assert SIA_BASE_URL.startswith("https://")

    def test_adf_ads_page_id(self) -> None:
        """Test Oracle ADF page ID constant.

        Verifies the ADF (Application Development Framework) page ID
        used in Oracle's partial page rendering system is set to "1".
        """
        assert ADF_ADS_PAGE_ID == "1"
        assert isinstance(ADF_ADS_PAGE_ID, str)

    def test_electives_campus_increment(self) -> None:
        """Test electives campus code offset value.

        Verifies the numeric offset (40) used to calculate campus codes
        when querying elective courses in the SIA system.
        """
        assert ELECTIVES_CAMPUS_INCREMENT == 40
        assert isinstance(ELECTIVES_CAMPUS_INCREMENT, int)


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


@pytest.mark.unit
class TestComponentIds:
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
        assert SHOW_CURSES_BTTN_ID.startswith("pt1:r1:0:cb")
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
            SHOW_CURSES_BTTN_ID,
            FACULTY_CAREER_DD_ID,
            CAMPUS_ELECTIVES_DD_ID,
            SELECT_ROW_ID,
            BACK_BTTN_ID,
        ]
        assert len(component_ids) == len(set(component_ids))


@pytest.mark.unit
class TestEventXmlPayloads:
    """Test Oracle RichClient event XML payloads."""

    def test_dropdown_event_value(self) -> None:
        """Test dropdown event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in DROPDOWN_EVENT_VALUE
        assert '<k v="type"><s>valueChange</s></k>' in DROPDOWN_EVENT_VALUE
        assert '<k v="autoSubmit"><b>1</b></k>' in DROPDOWN_EVENT_VALUE
        assert "suppressMessageShow" in DROPDOWN_EVENT_VALUE

    def test_button_event_value(self) -> None:
        """Test button event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in BTTN_EVENT_VALUE
        assert '<k v="type"><s>action</s></k>' in BTTN_EVENT_VALUE

    def test_select_row_event_value(self) -> None:
        """Test row selection event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in SELECT_ROW_EVENT_VALUE
        assert '<k v="type"><s>selection</s></k>' in SELECT_ROW_EVENT_VALUE

    def test_event_values_are_xml_formatted(self) -> None:
        """Test that all event values are valid XML fragments."""
        event_values = [DROPDOWN_EVENT_VALUE, BTTN_EVENT_VALUE, SELECT_ROW_EVENT_VALUE]
        for event in event_values:
            assert event.startswith('<m xmlns="http://oracle.com/richClient/comm">')
            assert event.endswith("</m>")


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

        # All values should be tuples of (component_id, event_xml)
        for _key, value in DATA_MAP.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)  # component_id
            assert isinstance(value[1], str)  # event_xml

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


@pytest.mark.unit
class TestSiaHeaders:
    """Test SIA HTTP headers configuration."""

    def test_sia_headers_structure(self) -> None:
        """Test SIA_HEADERS is a dictionary."""
        assert isinstance(SIA_HEADERS, dict)
        assert len(SIA_HEADERS) > 0

    def test_required_headers_present(self) -> None:
        """Test required Oracle ADF headers are present."""
        required_headers = [
            "authority",
            "accept",
            "adf-ads-page-id",
            "adf-rich-message",
            "content-type",
            "origin",
            "referer",
            "user-agent",
        ]

        for header in required_headers:
            assert header in SIA_HEADERS, f"Header {header} not found in SIA_HEADERS"

    def test_adf_specific_headers(self) -> None:
        """Test Oracle ADF-specific headers have correct values."""
        assert SIA_HEADERS["adf-ads-page-id"] == ADF_ADS_PAGE_ID
        assert SIA_HEADERS["adf-rich-message"] == "true"

    def test_content_type_header(self) -> None:
        """Test content-type header is set for form submission."""
        assert "application/x-www-form-urlencoded" in SIA_HEADERS["content-type"]
        assert "charset=UTF-8" in SIA_HEADERS["content-type"]

    def test_origin_and_referer(self) -> None:
        """Test origin and referer headers match SIA domain."""
        assert SIA_HEADERS["origin"] == "https://sia.unal.edu.co"
        assert SIA_HEADERS["referer"] == SIA_BASE_URL

    def test_security_headers_present(self) -> None:
        """Test security-related headers are present."""
        security_headers = ["sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"]
        for header in security_headers:
            assert header in SIA_HEADERS


@pytest.mark.unit
class TestSiaSessionStatus:
    """Test SiaSessionStatus enumeration."""

    def test_session_status_is_enum(self) -> None:
        """Test SiaSessionStatus is an Enum class."""
        from enum import Enum

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


@pytest.mark.unit
class TestConstantsIntegrity:
    """Test cross-constant integrity and relationships."""

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

        # All dropdown actions should end with '_DD'
        for action in dropdown_actions:
            assert action.endswith("_DD")

    def test_url_validity(self) -> None:
        """Test SIA base URL is accessible (structure test only)."""
        assert SIA_BASE_URL.startswith("https://")
        assert "sia.unal.edu.co" in SIA_BASE_URL
        assert ".jsf" in SIA_BASE_URL
