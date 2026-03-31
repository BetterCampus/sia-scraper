"""Rust/Python parity tests - compare outputs from Rust extension vs Python implementation."""

import pytest
from sia_scraper_rust import extract_view_state as rust_extract_view_state
from sia_scraper_rust import get_course_list as rust_get_course_list
from sia_scraper_rust import parse_course_info as rust_parse_course_info
from sia_scraper_rust import parse_prereqs as rust_parse_prereqs

from sia_scraper.constants import business
from sia_scraper.core.adf_state import extract_view_state as python_extract_view_state
from sia_scraper.parsers.course_parser import scrape_info as python_scrape_info
from sia_scraper.parsers.course_parser import scrape_prereqs as python_scrape_prereqs
from sia_scraper.parsers.html_parser import get_course_list as python_get_course_list


class TestExtractViewStateParity:
    """Compare Rust and Python extract_view_state outputs."""

    def test_extract_view_state_string_parity(self):
        html = '<input type="hidden" name="javax.faces.ViewState" value="abc123def456">'
        rust_result = rust_extract_view_state(html)
        python_result = python_extract_view_state(html)
        assert rust_result == python_result

    def test_extract_view_state_bytes_parity(self):
        html_bytes = b'<input type="hidden" name="javax.faces.ViewState" value="xyz789">'
        rust_result = rust_extract_view_state(html_bytes.decode("utf-8"))
        python_result = python_extract_view_state(html_bytes)
        assert rust_result == python_result


class TestParseCourseInfoParity:
    """Compare Rust and Python parse_course_info outputs."""

    def test_course_name_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_result["course_name"] == python_result.course_name
        assert rust_result["course_name"] is not None
        assert len(rust_result["course_name"]) > 0

    def test_credits_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_result["credits"] == python_result.credits

    def test_typology_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_result["typology"] == python_result.typology

    def test_groups_count_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert len(rust_result["groups"]) == len(python_result.groups)

    def test_available_spots_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_result["available_spots"] == python_result.available_spots


class TestParsePrereqsParity:
    """Compare Rust and Python parse_prereqs outputs."""

    def test_prereqs_course_name_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert rust_result["course_name"] == python_result.course_name

    def test_prereqs_credits_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert rust_result["credits"] == python_result.credits

    def test_conditions_count_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert len(rust_result["conditions"]) == len(python_result.conditions)

    def test_condition_header_fields_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert rust_result["conditions"]
        assert python_result.conditions

        rust_condition = rust_result["conditions"][0]
        python_condition = python_result.conditions[0]

        assert int(rust_condition["condition"].strip("[]")) == python_condition.condition
        assert rust_condition["type"].strip("[]") == python_condition.type.value
        assert rust_condition["all_required"].strip("[]").upper() == (
            "S" if python_condition.all_required else "N"
        )
        assert (
            int(rust_condition["number_of_courses"].strip("[]"))
            == python_condition.number_of_courses
        )


class TestGetCourseListParity:
    """Compare Rust and Python get_course_list outputs."""

    def test_course_list_count_parity(self, sia_career_page_regular_html):
        rust_result = rust_get_course_list(sia_career_page_regular_html)
        python_result = python_get_course_list(sia_career_page_regular_html)

        assert len(rust_result) == len(python_result)

    def test_course_list_content_parity(self, sia_career_page_regular_html):
        rust_result = rust_get_course_list(sia_career_page_regular_html)
        python_result = python_get_course_list(sia_career_page_regular_html)

        assert rust_result == python_result

    def test_course_list_bytes_input(self, sia_career_page_regular_html):
        rust_result = rust_get_course_list(sia_career_page_regular_html)
        assert len(rust_result) > 0

    def test_course_list_string_input(self, sia_career_page_regular_html):
        html_str = sia_career_page_regular_html.decode("utf-8")
        rust_result = rust_get_course_list(html_str)
        assert len(rust_result) > 0

    def test_course_list_empty_html(self):
        html = "<html><body><p>No courses here</p></body></html>"
        rust_result = rust_get_course_list(html)
        python_result = python_get_course_list(html)
        assert rust_result == python_result
        assert len(rust_result) == 0


class TestRustErrors:
    """Test Rust error handling matches Python."""

    def test_extract_view_state_missing_raises(self):
        import sia_scraper_rust

        html = "<div>No ViewState here</div>"
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            rust_extract_view_state(html)


class TestPythonRustConstantParity:
    """Validate Python constants match Rust constant values."""

    def test_electives_campus_increment_parity(self) -> None:
        """ELECTIVES_CAMPUS_INCREMENT must be 40 in both Python and Rust."""
        assert business.ELECTIVES_CAMPUS_INCREMENT == 40

    def test_group_indices_parity(self) -> None:
        """Group index constants must match between Python and Rust."""
        assert business.GROUP_TEACHER_INDEX == 0
        assert business.GROUP_FACULTY_INDEX == 1
        assert business.GROUP_SCHEDULES_INDEX == 2
        assert business.GROUP_DURATION_INDEX == 3
        assert business.GROUP_SCHEDULE_TYPE_INDEX == 4
        assert business.GROUP_SPOTS_INDEX == 5
        assert business.MIN_GROUP_DATA_LENGTH_WITH_SPOTS == 6

    def test_faculty_career_default_index_parity(self) -> None:
        """FACULTY_CAREER_DEFAULT_INDEX must be '0' in both Python and Rust."""
        assert business.FACULTY_CAREER_DEFAULT_INDEX == "0"

    def test_course_column_indices_parity(self) -> None:
        """Course table column indices must match."""
        assert business.COURSE_CODE_COL == 0
        assert business.COURSE_NAME_COL == 1
