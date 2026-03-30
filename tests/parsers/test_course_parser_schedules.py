"""Focused edge-case tests for schedule and group extraction internals."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from sia_scraper.parsers.course_parser import _extract_group, _extract_schedules
from sia_scraper.parsers.html_parser import HtmlElement


@pytest.mark.unit
class TestExtractSchedulesEdgeCases:
    """Cover defensive branches in schedule extraction."""

    def test_extract_schedules_skips_when_schedule_span_is_missing(self) -> None:
        """Skip rows when nested classroom exists but schedule span lookup fails."""
        lista_span = MagicMock()
        lista_span.findall.return_value = [MagicMock()]
        lista_span.find.return_value = None

        schedule_section = MagicMock()
        schedule_section.findall.return_value = [lista_span]

        group_data = cast(list[HtmlElement], [MagicMock(), MagicMock(), schedule_section])

        assert _extract_schedules(group_data) == []

    def test_extract_schedules_skips_when_schedule_text_format_is_invalid(self) -> None:
        """Skip rows when schedule text does not match expected regex format."""
        schedule_span = MagicMock()
        schedule_span.text_content.return_value = "LUNES 07:00-09:00"

        classroom_span = MagicMock()
        classroom_span.text_content.return_value = "401-101"

        lista_span = MagicMock()

        def _find_side_effect(tag: str) -> MagicMock | None:
            if tag == "span":
                return schedule_span
            if tag == "span[@class='lista-elemento']":
                return classroom_span
            return None

        lista_span.findall.return_value = [classroom_span]
        lista_span.find.side_effect = _find_side_effect

        schedule_section = MagicMock()
        schedule_section.findall.return_value = [lista_span]

        group_data = cast(list[HtmlElement], [MagicMock(), MagicMock(), schedule_section])

        assert _extract_schedules(group_data) == []


@pytest.mark.unit
class TestExtractGroupEdgeCases:
    """Cover less common branches in group extraction."""

    def test_extract_group_uses_unknown_group_name_when_parent_is_none(self) -> None:
        """Use default group name when group element has no parent."""
        teacher_span = MagicMock()
        teacher_span.text_content.return_value = "Teacher"

        teacher_item = MagicMock()
        teacher_item.findall.return_value = [teacher_span]

        faculty_span = MagicMock()
        faculty_span.text_content.return_value = "Engineering"
        faculty_item = MagicMock()
        faculty_item.findall.return_value = [faculty_span]

        schedule_section = MagicMock()
        schedule_section.findall.return_value = []

        duration_span = MagicMock()
        duration_span.text_content.return_value = "16 weeks"
        duration_item = MagicMock()
        duration_item.findall.return_value = [duration_span]

        schedule_type_span = MagicMock()
        schedule_type_span.text_content.return_value = "In-person"
        schedule_type_item = MagicMock()
        schedule_type_item.findall.return_value = [schedule_type_span]

        spots_span = MagicMock()
        spots_span.text_content.return_value = "12"
        spots_item = MagicMock()
        spots_item.findall.return_value = [spots_span]

        panel_div = [
            teacher_item,
            faculty_item,
            schedule_section,
            duration_item,
            schedule_type_item,
            spots_item,
        ]

        group = MagicMock()
        group.parent = None

        def _group_find_side_effect(tag: str, class_: str | None = None) -> list[MagicMock] | None:
            if tag == "div" and class_ == "af_panelGroupLayout":
                return panel_div  # type: ignore[return-value]
            return None

        group.find.side_effect = _group_find_side_effect

        result = _extract_group(group, "Course X")

        assert result is not None
        assert result.group_name == "Unknown"
        assert result.teacher == "Teacher"
        assert result.spots == 12
