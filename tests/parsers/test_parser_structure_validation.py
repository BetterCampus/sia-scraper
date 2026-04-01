"""Fixture structure validation tests.

These tests verify that our assumptions about SIA's HTML/XML structure
hold across all test fixtures. If these tests fail, it indicates:
1. SIA changed their HTML structure, OR
2. We captured a fixture with unusual structure

These tests act as "canaries" - they fail early if structural assumptions
no longer hold, before functional tests fail mysteriously.
"""

from pathlib import Path

import pytest

from sia_scraper.constants.business import (
    GROUP_DURATION_INDEX,
    GROUP_FACULTY_INDEX,
    GROUP_SCHEDULE_TYPE_INDEX,
    GROUP_SCHEDULES_INDEX,
    GROUP_SPOTS_INDEX,
    GROUP_TEACHER_INDEX,
    MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
)
from sia_scraper.parsers.html_parser import HtmlParser


@pytest.fixture
def all_course_detail_fixtures() -> list[str]:
    """Collect all course detail fixtures for batch validation."""
    fixtures_dir = Path("tests/fixtures/xml")
    fixtures = []
    for fixture_file in sorted(fixtures_dir.glob("course_detail_*.xml")):
        content = fixture_file.read_text()
        # Extract CDATA content
        start = content.find("<![CDATA[") + 9
        end = content.find("]]>")
        if start > 8 and end > start:
            fixtures.append(content[start:end])
    return fixtures


@pytest.fixture
def all_prereq_fixtures() -> list[str]:
    """Collect all prerequisite fixtures for batch validation."""
    fixtures_dir = Path("tests/fixtures/xml")
    fixtures = []
    for fixture_file in sorted(fixtures_dir.glob("course_prereqs_*.xml")):
        content = fixture_file.read_text()
        # Extract CDATA content
        start = content.find("<![CDATA[") + 9
        end = content.find("]]>")
        if start > 8 and end > start:
            fixtures.append(content[start:end])
    return fixtures


@pytest.mark.unit
class TestGroupPanelStructure:
    """Validate group panel div structure assumptions."""

    def test_all_groups_have_expected_div_count(
        self, all_course_detail_fixtures: list[str]
    ) -> None:
        """Verify all groups in fixtures have 5-6 divs.

        Assumption: Group panels have either:
        - 5 divs (no spots info) or
        - 6 divs (full info including spots)

        If this fails, SIA may have changed their layout or we captured
        an unusual fixture.
        """
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)
            groups = parser.css_select(".af_showDetailHeader_content0")

            for i, group in enumerate(groups):
                panel = group.find("div", class_="af_panelGroupLayout")
                if panel is None:
                    continue

                divs = list(panel)
                assert 5 <= len(divs) <= 6, (
                    f"Fixture {idx}, group {i} has unexpected div count: {len(divs)}. "
                    f"Expected 5-6 divs. "
                    f"Div contents: {[d.text_content()[:40] for d in divs]}"
                )

    def test_group_div_order_matches_constants(self, all_course_detail_fixtures: list[str]) -> None:
        """Verify div order matches our GROUP_*_INDEX constants.

        This test validates that the positional indexes we use for extraction
        actually correspond to the correct fields in the HTML.
        """
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)
            groups = parser.css_select(".af_showDetailHeader_content0")

            if not groups:
                continue

            # Check first group in each fixture
            group = groups[0]
            panel = group.find("div", class_="af_panelGroupLayout")
            assert panel is not None, f"Fixture {idx}: Group panel not found"

            divs = list(panel)
            if len(divs) < MIN_GROUP_DATA_LENGTH_WITH_SPOTS:
                continue

            # Validate each index contains the expected field
            teacher_text = divs[GROUP_TEACHER_INDEX].text_content()
            assert "Profesor:" in teacher_text or "PROFESOR:" in teacher_text, (
                f"Fixture {idx}: Index {GROUP_TEACHER_INDEX} expected 'Profesor:', got: {teacher_text[:50]}"
            )

            faculty_text = divs[GROUP_FACULTY_INDEX].text_content()
            # Faculty can be empty but div should exist
            assert (
                "Facultad:" in faculty_text
                or "FACULTAD:" in faculty_text
                or faculty_text.strip() == ""
            ), f"Fixture {idx}: Index {GROUP_FACULTY_INDEX} unexpected: {faculty_text[:50]}"

            schedules_text = divs[GROUP_SCHEDULES_INDEX].text_content()
            assert "Horarios" in schedules_text or "HORARIOS" in schedules_text, (
                f"Fixture {idx}: Index {GROUP_SCHEDULES_INDEX} expected 'Horarios', got: {schedules_text[:50]}"
            )

            duration_text = divs[GROUP_DURATION_INDEX].text_content()
            assert "Duración:" in duration_text or "DURACIÓN:" in duration_text, (
                f"Fixture {idx}: Index {GROUP_DURATION_INDEX} expected 'Duración:', got: {duration_text[:50]}"
            )

            schedule_type_text = divs[GROUP_SCHEDULE_TYPE_INDEX].text_content()
            assert "Jornada:" in schedule_type_text or "JORNADA:" in schedule_type_text, (
                f"Fixture {idx}: Index {GROUP_SCHEDULE_TYPE_INDEX} expected 'Jornada:', got: {schedule_type_text[:50]}"
            )

            if len(divs) >= MIN_GROUP_DATA_LENGTH_WITH_SPOTS:
                spots_text = divs[GROUP_SPOTS_INDEX].text_content()
                assert "Cupos" in spots_text or "CUPOS" in spots_text, (
                    f"Fixture {idx}: Index {GROUP_SPOTS_INDEX} expected 'Cupos', got: {spots_text[:50]}"
                )

    def test_no_groups_have_fewer_than_five_divs(
        self, all_course_detail_fixtures: list[str]
    ) -> None:
        """Verify no groups have fewer than 5 divs.

        Assumption: Even minimal groups have at least teacher, faculty,
        schedules, duration, and schedule_type (5 fields).

        If this fails, we need to handle ultra-minimal groups.
        """
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)
            groups = parser.css_select(".af_showDetailHeader_content0")

            for i, group in enumerate(groups):
                panel = group.find("div", class_="af_panelGroupLayout")
                if panel is None:
                    continue

                divs = list(panel)
                assert len(divs) >= 5, (
                    f"Fixture {idx}, group {i} has only {len(divs)} divs (expected minimum 5). "
                    f"Contents: {[d.text_content()[:30] for d in divs]}"
                )


@pytest.mark.unit
class TestPrerequisiteConditionStructure:
    """Validate prerequisite condition header structure."""

    def test_all_conditions_have_four_headers(self, all_prereq_fixtures: list[str]) -> None:
        """Verify all prerequisite conditions have exactly 4 header fields.

        Assumption: Prerequisite conditions always have:
        1. Condición (condition type)
        2. Tipo (prerequisite type)
        3. ¿Todas? (all required flag)
        4. Número de materias/créditos (number required)
        """
        for idx, fixture_xml in enumerate(all_prereq_fixtures):
            parser = HtmlParser(fixture_xml)

            # Find condition containers
            condition_divs = parser.css_select(
                "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout"
            )

            for i, cdiv in enumerate(condition_divs):
                sub_divs = list(cdiv)
                if not sub_divs:
                    continue

                headers = sub_divs[0].css_select("span.strong.af_panelGroupLayout > span.margin-l")

                assert len(headers) == 4, (
                    f"Fixture {idx}, condition {i} has {len(headers)} headers "
                    f"(expected 4). Header texts: {[h.text_content() for h in headers]}"
                )

    def test_condition_header_order_is_consistent(self, all_prereq_fixtures: list[str]) -> None:
        """Verify condition headers appear in expected order."""
        for idx, fixture_xml in enumerate(all_prereq_fixtures):
            parser = HtmlParser(fixture_xml)

            condition_divs = parser.css_select(
                "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout"
            )

            if not condition_divs:
                continue

            # Check first condition
            sub_divs = list(condition_divs[0])
            if not sub_divs:
                continue

            headers = sub_divs[0].css_select("span.strong.af_panelGroupLayout > span.margin-l")

            if len(headers) < 4:
                continue

            # Validate header text content
            header_texts = [h.text_content().strip() for h in headers[:4]]

            assert "Condición" in header_texts[0] or "CONDICIÓN" in header_texts[0], (
                f"Fixture {idx}: First header expected 'Condición', got: {header_texts[0]}"
            )
            assert "Tipo" in header_texts[1] or "TIPO" in header_texts[1], (
                f"Fixture {idx}: Second header expected 'Tipo', got: {header_texts[1]}"
            )
            assert "Todas" in header_texts[2] or "TODAS" in header_texts[2], (
                f"Fixture {idx}: Third header expected 'Todas', got: {header_texts[2]}"
            )


@pytest.mark.unit
class TestCourseBasicFieldsPresent:
    """Validate that basic course fields are always present."""

    def test_all_courses_have_credits_element(self, all_course_detail_fixtures: list[str]) -> None:
        """Verify all course detail pages have credits element."""
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)
            credits_elem = parser.find("span", class_="detass-creditos")

            assert credits_elem is not None, (
                f"Fixture {idx}: Credits element <span class='detass-creditos'> not found"
            )

    def test_all_courses_have_name_element(self, all_course_detail_fixtures: list[str]) -> None:
        """Verify all course detail pages have course name."""
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)

            # Try primary selector
            name_elem = parser.find("h2")

            assert name_elem is not None and len(name_elem.text_content().strip()) > 0, (
                f"Fixture {idx}: Course name element <h2> not found or empty"
            )

    def test_all_courses_have_tipologia_element(
        self, all_course_detail_fixtures: list[str]
    ) -> None:
        """Verify all course detail pages have typology element."""
        for idx, fixture_xml in enumerate(all_course_detail_fixtures):
            parser = HtmlParser(fixture_xml)
            tipologia_elem = parser.find("span", class_="detass-tipologia")

            assert tipologia_elem is not None, (
                f"Fixture {idx}: Typology element <span class='detass-tipologia'> not found"
            )
