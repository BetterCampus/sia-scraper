"""Tests for typed Rust JSON bridge parser endpoint."""

import pytest

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

        with pytest.raises(Exception) as exc_info:  # noqa: B017 - PyO3 raises runtime-like error
            scrape_info_typed(xml)

        error_msg = str(exc_info.value)
        assert "teacher" in error_msg.lower()
        assert "html snippet" in error_msg.lower()
        assert "stack" in error_msg.lower()
