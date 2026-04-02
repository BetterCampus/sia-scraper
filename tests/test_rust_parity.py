"""Rust/Python parity tests - compare outputs from Rust extension vs Python implementation."""

from typing import Any, cast

import pytest

from sia_scraper.constants import business
from sia_scraper.core.adf_state import extract_view_state as python_extract_view_state
from sia_scraper.models.course import CourseInfoTyped
from sia_scraper.models.prerequisite import CoursePrereqsTyped
from sia_scraper.parsers.course_parser import scrape_info as python_scrape_info
from sia_scraper.parsers.course_parser import scrape_prereqs as python_scrape_prereqs
from sia_scraper_rust import extract_view_state as rust_extract_view_state
from sia_scraper_rust import parse_course_info as rust_parse_course_info
from sia_scraper_rust import parse_course_info_json as rust_parse_course_info_json
from sia_scraper_rust import parse_prereqs as rust_parse_prereqs
from sia_scraper_rust import parse_prereqs_json as rust_parse_prereqs_json


def _course_to_dict(course: Any) -> dict[str, object]:
    return {
        "course_name": course.course_name,
        "credits": course.credits,
        "typology": course.typology,
        "available_spots": course.available_spots,
        "groups": [
            {
                "group_name": group.group_name,
                "teacher": group.teacher,
                "faculty": group.faculty,
                "course_name": group.course_name,
                "duration": group.duration,
                "schedule_type": group.schedule_type,
                "spots": group.spots,
                "code": group.code,
                "schedules": [
                    {
                        "day": s.day,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "classroom": s.classroom,
                    }
                    for s in group.schedules
                ],
            }
            for group in course.groups
        ],
    }


def _prereqs_to_dict(prereqs: Any) -> dict[str, object]:
    return {
        "course_name": prereqs.course_name,
        "credits": prereqs.credits,
        "typology": prereqs.typology,
        "conditions": [
            {
                "condition": condition.condition,
                "type": condition.prereq_type,
                "all_required": condition.all_required,
                "number_of_courses": condition.number_of_courses,
                "prerequisites": [
                    {
                        "course_code": p.course_code,
                        "course_name": p.course_name,
                    }
                    for p in condition.prerequisites
                ],
            }
            for condition in prereqs.conditions
        ],
    }


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
        rust_dict = _course_to_dict(rust_result)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_dict["course_name"] == python_result.course_name
        assert rust_dict["course_name"] is not None
        assert len(str(rust_dict["course_name"])) > 0

    def test_credits_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        rust_dict = _course_to_dict(rust_result)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_dict["credits"] == python_result.credits

    def test_typology_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        rust_dict = _course_to_dict(rust_result)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_dict["typology"] == python_result.typology

    def test_groups_count_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        rust_dict = _course_to_dict(rust_result)
        python_result = python_scrape_info(sia_course_detail_xml)

        groups = cast(list[dict[str, object]], rust_dict["groups"])
        assert len(groups) == len(python_result.groups)

    def test_available_spots_parity(self, sia_course_detail_xml):
        rust_result = rust_parse_course_info(sia_course_detail_xml)
        rust_dict = _course_to_dict(rust_result)
        python_result = python_scrape_info(sia_course_detail_xml)

        assert rust_dict["available_spots"] == python_result.available_spots


class TestParsePrereqsParity:
    """Compare Rust and Python parse_prereqs outputs."""

    def test_prereqs_course_name_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        rust_dict = _prereqs_to_dict(rust_result)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert rust_dict["course_name"] == python_result.course_name

    def test_prereqs_credits_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        rust_dict = _prereqs_to_dict(rust_result)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert rust_dict["credits"] == python_result.credits

    def test_conditions_count_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        rust_dict = _prereqs_to_dict(rust_result)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        conditions = cast(list[dict[str, object]], rust_dict["conditions"])
        assert len(conditions) == len(python_result.conditions)

    def test_condition_header_fields_parity(self, sia_course_prereqs_xml):
        rust_result = rust_parse_prereqs(sia_course_prereqs_xml)
        rust_dict = _prereqs_to_dict(rust_result)
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        conditions = cast(list[dict[str, object]], rust_dict["conditions"])
        assert conditions
        assert python_result.conditions

        rust_condition = conditions[0]
        python_condition = python_result.conditions[0]

        rust_condition_number = cast(int, rust_condition["condition"])
        rust_num_courses = cast(int, rust_condition["number_of_courses"])

        assert int(rust_condition_number) == python_condition.condition
        assert str(rust_condition["type"]) == python_condition.type.value
        assert bool(rust_condition["all_required"]) is python_condition.all_required
        assert int(rust_num_courses) == python_condition.number_of_courses

    def test_typed_prereqs_model_parity(self, sia_course_prereqs_xml):
        rust_model = rust_parse_prereqs(sia_course_prereqs_xml)
        typed = CoursePrereqsTyped.model_validate(_prereqs_to_dict(rust_model))
        python_result = python_scrape_prereqs(sia_course_prereqs_xml)

        assert typed.course_name == python_result.course_name
        assert typed.credits == python_result.credits
        assert len(typed.conditions) == len(python_result.conditions)

    def test_typed_prereqs_model_invalid_raises(self):
        with pytest.raises(Exception):  # noqa: B017 - PyO3 runtime exception path
            rust_parse_prereqs("<div></div>")


class TestDeprecatedJsonParsers:
    """Ensure deprecated JSON parser endpoints still behave as documented."""

    def test_parse_course_info_json_warns_and_matches_typed_contract(self, sia_course_detail_xml):
        with pytest.warns(DeprecationWarning):
            rust_json = rust_parse_course_info_json(sia_course_detail_xml)

        typed = CourseInfoTyped.model_validate_json(rust_json)
        rust_model = rust_parse_course_info(sia_course_detail_xml)
        rust_dict = _course_to_dict(rust_model)

        assert typed.course_name == rust_dict["course_name"]
        assert typed.credits == rust_dict["credits"]

    def test_parse_prereqs_json_warns_and_matches_typed_contract(self, sia_course_prereqs_xml):
        with pytest.warns(DeprecationWarning):
            rust_json = rust_parse_prereqs_json(sia_course_prereqs_xml)

        typed = CoursePrereqsTyped.model_validate_json(rust_json)
        rust_model = rust_parse_prereqs(sia_course_prereqs_xml)
        rust_dict = _prereqs_to_dict(rust_model)

        assert typed.course_name == rust_dict["course_name"]
        assert typed.credits == rust_dict["credits"]


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
