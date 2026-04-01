"""Regression tests comparing parser outputs against captured baselines."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sia_scraper.parsers import get_course_list, scrape_info, scrape_prereqs
from sia_scraper.parsers.models import PrereqType


@pytest.fixture
def parser_baseline(
    fixture_path: Path,
    latest_fixture_date: str,
) -> dict[str, object]:
    baseline_path = fixture_path / "baselines" / f"parser_baseline_{latest_fixture_date}.json"
    if not baseline_path.exists():
        baseline_dates: list[str] = []
        pattern = re.compile(r"parser_baseline_(\d{4}-\d{2}-\d{2})\.json$")
        for path in sorted((fixture_path / "baselines").glob("parser_baseline_*.json")):
            match = pattern.search(path.name)
            if match is not None:
                baseline_dates.append(match.group(1))

        details = ", ".join(baseline_dates) if baseline_dates else "none"
        pytest.skip(
            "Baseline for latest fixture date is missing. "
            f"Expected: {baseline_path.name}. Available baseline dates: {details}."
        )
    return json.loads(baseline_path.read_text(encoding="utf-8"))


@pytest.mark.unit
class TestParserRegression:
    """Ensure parser behavior stays stable for captured fixtures."""

    def test_scrape_info_matches_baseline(
        self, sia_course_detail_xml: str, parser_baseline: dict[str, object]
    ):
        parsed = scrape_info(sia_course_detail_xml)
        expected = parser_baseline["course_info"]
        assert isinstance(expected, dict)

        assert parsed.course_name == expected["course_name"]
        assert parsed.credits == expected["credits"]
        assert parsed.typology == expected["typology"]
        assert len(parsed.groups) == expected["groups_count"]
        assert parsed.available_spots == expected["available_spots"]

        first_group = expected["first_group"]
        assert isinstance(first_group, dict)
        assert parsed.groups[0].group_name == first_group["group_name"]
        assert parsed.groups[0].teacher == first_group["teacher"]
        assert parsed.groups[0].spots == first_group["spots"]
        assert len(parsed.groups[0].schedules) == first_group["schedules_count"]

    def test_scrape_prereqs_matches_baseline(
        self,
        sia_course_prereqs_xml: str,
        parser_baseline: dict[str, object],
    ):
        parsed = scrape_prereqs(sia_course_prereqs_xml)
        expected = parser_baseline["course_prereqs"]
        assert isinstance(expected, dict)

        assert parsed.course_name == expected["course_name"]
        assert parsed.code == expected["code"]
        assert parsed.credits == expected["credits"]
        assert parsed.typology == expected["typology"]
        assert len(parsed.conditions) == expected["conditions_count"]

        first_condition = expected["first_condition"]
        assert isinstance(first_condition, dict)
        assert parsed.conditions[0].condition == int(str(first_condition["condition"]).strip("[]"))
        assert parsed.conditions[0].type == PrereqType(str(first_condition["type"]).strip("[]"))
        raw_all_required = (
            str(first_condition.get("all_required", "")).strip("[]").upper().replace(" ", "")
        )
        expected_all_required = raw_all_required in {"S", "SI"}
        assert parsed.conditions[0].all_required is expected_all_required
        assert parsed.conditions[0].number_of_courses == int(
            str(first_condition["number_of_courses"]).strip("[]")
        )
        assert len(parsed.conditions[0].prerequisites) == first_condition["prerequisites_count"]

        first_prereq = expected["first_prerequisite"]
        assert isinstance(first_prereq, dict)
        assert parsed.conditions[0].prerequisites[0].course_code == first_prereq["course_code"]
        assert parsed.conditions[0].prerequisites[0].course_name == first_prereq["course_name"]

    def test_get_course_list_matches_baseline(
        self,
        sia_career_page_regular_html: bytes,
        parser_baseline: dict[str, object],
    ):
        parsed = get_course_list(sia_career_page_regular_html)
        expected = parser_baseline["course_list_regular"]
        assert isinstance(expected, dict)

        assert len(parsed) == expected["count"]
        assert parsed[0] == expected["first"]
