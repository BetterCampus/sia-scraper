"""Validation tests for captured and sanitized SIA fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from lxml import etree

from sia_scraper.parsers import HtmlParser
from sia_scraper.parsers.course_parser import scrape_info


def _dated_fixture_files(fixture_path: Path, latest_fixture_date: str) -> list[Path]:
    files = [
        *sorted((fixture_path / "html").glob(f"*_{latest_fixture_date}.html")),
        *sorted((fixture_path / "xml").glob(f"*_{latest_fixture_date}.xml")),
        *sorted((fixture_path / "json").glob(f"*_{latest_fixture_date}.json")),
    ]
    if not files:
        raise RuntimeError(f"No fixture files found for date {latest_fixture_date}")
    return files


@pytest.mark.unit
class TestFixturesWellFormed:
    """Fixture files can be parsed with expected parsers."""

    def test_html_fixtures_are_parseable(self, fixture_path: Path, latest_fixture_date: str):
        html_files = sorted((fixture_path / "html").glob(f"*_{latest_fixture_date}.html"))
        assert html_files

        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            parser = HtmlParser(content)
            assert parser.root is not None

    def test_xml_fixtures_are_parseable(self, fixture_path: Path, latest_fixture_date: str):
        xml_files = sorted((fixture_path / "xml").glob(f"*_{latest_fixture_date}.xml"))
        assert xml_files

        for xml_file in xml_files:
            content = xml_file.read_text(encoding="utf-8")
            parser = HtmlParser(content)
            assert parser.root is not None

    def test_json_fixtures_are_valid_json(self, fixture_path: Path, latest_fixture_date: str):
        json_files = sorted((fixture_path / "json").glob(f"*_{latest_fixture_date}.json"))
        assert json_files

        for json_file in json_files:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            assert isinstance(data, (dict, list))


@pytest.mark.unit
class TestFixturesSanitized:
    """Fixture files do not contain live session identifiers."""

    def test_fixtures_include_sanitized_placeholders(
        self,
        fixture_path: Path,
        latest_fixture_date: str,
    ):
        combined_content = "\n".join(
            file.read_text(encoding="utf-8", errors="ignore")
            for file in _dated_fixture_files(fixture_path, latest_fixture_date)
        )

        assert "SANITIZED_VIEWSTATE_TOKEN_12345" in combined_content
        assert "SANITIZED_WINDOW_ID_67890" in combined_content
        assert "SANITIZED_PortalJSESSION_VALUE" in combined_content

    def test_no_unsanitized_portal_jsession_tokens(
        self,
        fixture_path: Path,
        latest_fixture_date: str,
    ):
        all_content = "\n".join(
            file.read_text(encoding="utf-8", errors="ignore")
            for file in _dated_fixture_files(fixture_path, latest_fixture_date)
        )
        leaked_tokens = re.findall(r"PortalJSESSION=(?!SANITIZED_)[^\s\"'<>;]+", all_content)
        assert leaked_tokens == []

    def test_no_unsanitized_window_id_in_session_data(
        self, sia_session_data_json: dict[str, object]
    ):
        params = sia_session_data_json.get("params")
        assert isinstance(params, dict)
        assert params.get("Adf-Window-Id") == "SANITIZED_WINDOW_ID_67890"

    def test_no_unsanitized_viewstate_in_session_data(
        self, sia_session_data_json: dict[str, object]
    ):
        view_state = sia_session_data_json.get("javax_faces_ViewState")
        assert view_state == "SANITIZED_VIEWSTATE_TOKEN_12345"


@pytest.mark.unit
class TestFixturesStructure:
    """Fixture files contain baseline structures expected by the scraper."""

    def test_initial_page_contains_oracle_adf_fields(self, sia_initial_html: bytes):
        html_text = sia_initial_html.decode("utf-8", errors="ignore")
        parser = HtmlParser(html_text)

        assert parser.find("input", name="javax.faces.ViewState") is not None
        assert parser.find("input", name="Adf-Window-Id") is not None
        assert parser.find("form") is not None

    def test_career_page_regular_contains_table_rows(self, sia_career_page_regular_html: bytes):
        parser = HtmlParser(sia_career_page_regular_html.decode("utf-8", errors="ignore"))
        rows = parser.find_all("tr", class_="af_table_data-row")
        assert len(rows) > 0

    def test_career_page_electives_contains_table_rows(self, sia_career_page_electives_html: bytes):
        parser = HtmlParser(sia_career_page_electives_html.decode("utf-8", errors="ignore"))
        rows = parser.find_all("tr", class_="af_table_data-row")
        assert len(rows) > 0

    def test_at_least_one_course_detail_fixture_is_parseable(
        self, sia_course_detail_xml_all: list[str]
    ):
        parseable_count = 0
        for course_xml in sia_course_detail_xml_all:
            try:
                parsed = scrape_info(course_xml)
            except ValueError:
                continue
            if parsed.course_name and parsed.credits >= 0:
                parseable_count += 1

        assert parseable_count > 0

    def test_course_prereqs_xml_has_course_title(self, sia_course_prereqs_xml: str):
        parser = HtmlParser(sia_course_prereqs_xml)
        h2_elements = parser.find_all("h2")
        assert len(h2_elements) > 0

    def test_adf_dropdown_xml_is_parseable_html(self, sia_adf_dropdown_xml: str):
        parser = HtmlParser(sia_adf_dropdown_xml)
        assert parser.root is not None

    def test_adf_error_xml_is_valid_xml(self, sia_adf_error_xml: str):
        root = etree.fromstring(sia_adf_error_xml.encode("utf-8"))
        assert root is not None

    def test_regular_course_list_json_non_empty(
        self, sia_course_list_regular_json: list[dict[str, str]]
    ):
        assert len(sia_course_list_regular_json) > 0
        assert all(isinstance(item, dict) and item for item in sia_course_list_regular_json)

    def test_elective_course_list_json_non_empty(
        self, sia_course_list_electives_json: list[dict[str, str]]
    ):
        assert len(sia_course_list_electives_json) > 0
        assert all(isinstance(item, dict) and item for item in sia_course_list_electives_json)

    def test_session_data_has_required_fields(self, sia_session_data_json: dict[str, object]):
        required_keys = {
            "STATUS",
            "career_code",
            "career_name",
            "is_electives",
            "javax_faces_ViewState",
            "params",
            "session_cookies",
            "session_headers",
        }
        assert required_keys.issubset(sia_session_data_json.keys())
