"""Contract tests validating expected Oracle ADF and SIA response structures."""

import pytest

from sia_scraper.parsers import HtmlParser
from sia_scraper.parsers.course_parser import scrape_info


@pytest.mark.unit
class TestSiaHtmlContracts:
    """Validate baseline structure in captured HTML pages."""

    def test_initial_page_has_hidden_viewstate(self, sia_initial_html: bytes):
        parser = HtmlParser(sia_initial_html.decode("utf-8", errors="ignore"))
        assert parser.find("input", name="javax.faces.ViewState") is not None

    def test_initial_page_has_hidden_window_id(self, sia_initial_html: bytes):
        parser = HtmlParser(sia_initial_html.decode("utf-8", errors="ignore"))
        assert parser.find("input", name="Adf-Window-Id") is not None

    def test_initial_page_has_study_level_dropdown(self, sia_initial_html: bytes):
        parser = HtmlParser(sia_initial_html.decode("utf-8", errors="ignore"))
        study_level = parser.find("select", id="pt1:r1:0:soc1::content")
        assert study_level is not None

    def test_career_page_has_course_rows(self, sia_career_page_regular_html: bytes):
        parser = HtmlParser(sia_career_page_regular_html.decode("utf-8", errors="ignore"))
        rows = parser.find_all("tr", class_="af_table_data-row")
        assert len(rows) > 0


@pytest.mark.unit
class TestOracleAdfContracts:
    """Validate baseline structure in captured Oracle ADF XML responses."""

    def test_course_detail_contains_partial_response_root(self, sia_course_detail_xml: str):
        assert "<partial-response>" in sia_course_detail_xml
        assert '<update id="pt1:r1">' in sia_course_detail_xml

    def test_at_least_one_course_detail_is_parseable(self, sia_course_detail_xml_all: list[str]):
        parseable_count = 0
        for course_xml in sia_course_detail_xml_all:
            try:
                parsed = scrape_info(course_xml)
            except ValueError:
                continue
            if parsed.course_name and parsed.credits >= 0:
                parseable_count += 1

        assert parseable_count > 0

    def test_prereqs_contains_partial_response_root(self, sia_course_prereqs_xml: str):
        assert "<partial-response>" in sia_course_prereqs_xml
        assert '<update id="pt1:r1">' in sia_course_prereqs_xml

    def test_adf_dropdown_response_contains_table_rows(self, sia_adf_dropdown_xml: str):
        assert "af_table_data-row" in sia_adf_dropdown_xml

    def test_adf_error_response_contains_error_envelope(self, sia_adf_error_xml: str):
        assert "<error>" in sia_adf_error_xml
        assert "InvalidStatus" in sia_adf_error_xml
