"""Tests for typed Rust PyClass bridge parser endpoint."""

from unittest.mock import patch

import pytest

import sia_scraper_rust
from sia_scraper.models.course import CourseInfoTyped
from sia_scraper.parsers.course_parser import scrape_info_typed


@pytest.mark.unit
class TestTypedCourseBridge:
    def test_scrape_info_typed_returns_typed_model(self, sia_course_detail_xml: str):
        result = scrape_info_typed(sia_course_detail_xml)

        assert isinstance(result, CourseInfoTyped)
        assert result.course_name != ""
        assert result.credits > 0
        assert result.available_spots >= 0

    def test_scrape_info_typed_raises_on_missing_required_group_teacher(self):
        xml = """
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div class="af_showDetailHeader_content0">
                    <div class="af_panelGroupLayout">
                        <div><span>Facultad: </span><span>CIENCIAS</span></div>
                    </div>
                </div>
            </body>
        </html>
        """

        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            scrape_info_typed(xml)

        error_msg = str(exc_info.value)
        assert "teacher" in error_msg.lower()
        assert "html snippet" in error_msg.lower()
        assert "stack" in error_msg.lower()

    def test_scrape_info_typed_uses_pyclass_endpoint_not_json(self):
        payload = {
            "course_name": "CALCULO",
            "credits": 4,
            "typology": "DISCIPLINAR OBLIGATORIA",
            "available_spots": 0,
            "scrape_timestamp": "2026-04-02 10:00",
            "groups": [],
            "code": None,
        }

        with (
            patch(
                "sia_scraper.parsers.course_parser.sia_scraper_rust.parse_course_info"
            ) as mock_parse,
            patch(
                "sia_scraper.parsers.course_parser._course_model_to_payload",
                return_value=payload,
            ) as mock_payload,
            patch(
                "sia_scraper.parsers.course_parser.sia_scraper_rust.parse_course_info_json"
            ) as mock_json,
        ):
            mock_parse.return_value = object()
            result = scrape_info_typed("<xml/>")

        assert isinstance(result, CourseInfoTyped)
        mock_parse.assert_called_once_with("<xml/>")
        mock_payload.assert_called_once()
        mock_json.assert_not_called()
