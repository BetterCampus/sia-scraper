"""Tests for typed Rust JSON bridge prerequisite endpoint."""

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
