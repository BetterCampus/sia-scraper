"""Tests for typed Rust PyClass bridge prerequisite endpoint."""

from unittest.mock import patch

import pytest

from sia_scraper.models.prerequisite import CoursePrereqsTyped
from sia_scraper.parsers.course_parser import scrape_prereqs_typed


@pytest.mark.unit
class TestTypedPrereqBridge:
    def test_scrape_prereqs_typed_returns_model(self, sia_course_prereqs_xml: str):
        result = scrape_prereqs_typed(sia_course_prereqs_xml)

        assert isinstance(result, CoursePrereqsTyped)
        assert result.course_name != ""
        assert result.credits > 0

    def test_scrape_prereqs_typed_raises_on_missing_name(self):
        with pytest.raises(Exception) as exc_info:  # noqa: B017 - PyO3 raises runtime-like error
            scrape_prereqs_typed("<div>invalid prereq body</div>")

        error_msg = str(exc_info.value).lower()
        assert "course_name" in error_msg
        assert "html snippet" in error_msg
        assert "stack" in error_msg

    def test_scrape_prereqs_typed_uses_pyclass_endpoint_not_json(self):
        payload = {
            "course_name": "CALCULO",
            "code": None,
            "credits": 4,
            "typology": "DISCIPLINAR OBLIGATORIA",
            "conditions": [],
        }

        with (
            patch("sia_scraper.parsers.course_parser.sia_scraper_rust.parse_prereqs") as mock_parse,
            patch(
                "sia_scraper.parsers.course_parser._prereqs_model_to_payload",
                return_value=payload,
            ) as mock_payload,
            patch(
                "sia_scraper.parsers.course_parser.sia_scraper_rust.parse_prereqs_json"
            ) as mock_json,
        ):
            mock_parse.return_value = object()
            result = scrape_prereqs_typed("<xml/>")

        assert isinstance(result, CoursePrereqsTyped)
        mock_parse.assert_called_once_with("<xml/>")
        mock_payload.assert_called_once()
        mock_json.assert_not_called()
