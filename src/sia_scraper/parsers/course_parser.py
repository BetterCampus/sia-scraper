"""Course information and prerequisite parsing functions.

This module provides functions for extracting course data from Oracle ADF XML/HTML
responses returned by SIA's web interface.
"""

import os
import re
from datetime import datetime
from typing import Any

from loguru import logger

import sia_scraper_rust

from ..constants.business import (
    GROUP_DURATION_INDEX,
    GROUP_FACULTY_INDEX,
    GROUP_SCHEDULE_TYPE_INDEX,
    GROUP_SCHEDULES_INDEX,
    GROUP_SPOTS_INDEX,
    GROUP_TEACHER_INDEX,
    MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
    REQUIRED_CONDITION_HEADERS,
)
from ..constants.defaults import (
    DEFAULT_DURATION,
    DEFAULT_FACULTY,
    DEFAULT_GROUP_NAME,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_TEACHER,
    DEFAULT_TYPOLOGY,
)
from ..models.course import CourseInfoTyped
from ..utils import format_date
from .html_parser import HtmlElement, HtmlParser
from .models import (
    CourseInfo,
    CoursePrereqs,
    Group,
    PrereqCondition,
    Prerequisite,
    Schedule,
)

# Enable logging only when SIA_DEBUG=1
if os.environ.get("SIA_DEBUG", "0") == "1":
    logger.enable("sia_scraper.parsers.course_parser")
else:
    logger.disable("sia_scraper.parsers.course_parser")

_SCHEDULE_REGEX = re.compile(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})")


def get_plain_text(xml: str) -> str:
    """Extract human-readable plain text from Oracle ADF XML response.

    ## Args
        xml: Raw XML/HTML from SIA Oracle ADF response.

    ## Returns
        Plain text content before the first triple non-breaking space separator.
    """
    return sia_scraper_rust.get_plain_text(xml)  # type: ignore[attr-defined]


def _extract_credits(parser: HtmlParser) -> int:
    """Extract credits from course XML.

    ## Args
        parser: HtmlParser instance with course XML loaded.

    ## Returns
        Credit hours as integer.

    ## Raises
        ValueError: If credits element or span not found in XML.
    """
    credits_elem = parser.find("span", class_="detass-creditos")
    if credits_elem is None:
        all_spans = parser.find_all("span")
        span_classes = list(set(span.get("class", "") for span in all_spans[:20]))

        logger.warning(
            "Credits element not found. Found {} span elements with classes: {}",
            len(all_spans),
            span_classes,
        )

        raise ValueError(
            f"Credits element not found in XML.\n"
            f"Searched for: <span class='detass-creditos'>\n"
            f"Found {len(all_spans)} span elements with classes: {span_classes}"
        )

    credits_spans = credits_elem.findall(".//span")
    if not credits_spans:
        logger.warning(
            "Credits span not found inside credits element. Content: {}",
            credits_elem.text_content()[:100],
        )

        raise ValueError(
            f"Credits span not found in XML.\n"
            f"Found credits element but no inner <span>.\n"
            f"Element content: {credits_elem.text_content()}"
        )

    credits_text = credits_spans[-1].text_content().strip()
    try:
        return int(credits_text)
    except ValueError as e:
        raise ValueError(
            f"Failed to parse credits value.\n"
            f"Expected integer, got: '{credits_text}'\n"
            f"Parse error: {e}"
        ) from e


def _extract_typology(parser: HtmlParser) -> str:
    """Extract typology from course XML.

    ## Args
        parser: HtmlParser instance with course XML loaded.

    ## Returns
        Course typology string, or "Unknown" if not found.
    """
    typology_elem = parser.find("span", class_="detass-tipologia")
    if typology_elem is None:
        return DEFAULT_TYPOLOGY
    typology_spans = typology_elem.findall(".//span")
    if not typology_spans:
        return DEFAULT_TYPOLOGY
    return _safe_text_content(typology_spans[-1], fallback=DEFAULT_TYPOLOGY)


def _safe_text_content(element: Any, fallback: str = "") -> str:
    """Safely extract text content from an element, ensuring a string return."""
    if element is None:
        return fallback
    try:
        text = element.text_content()
        return str(text).strip() if text else fallback
    except (AttributeError, TypeError):
        return fallback


def _extract_label_value(item: HtmlElement, fallback: str = DEFAULT_TYPOLOGY) -> str:
    spans = item.findall(".//span")
    if not spans:
        return fallback
    value = spans[-1].text_content().strip()
    return value if value else fallback


def _extract_schedules(group_data: list[HtmlElement]) -> list[Schedule]:
    """Extract schedules list from group data."""
    schedules: list[Schedule] = []

    if len(group_data) <= GROUP_SCHEDULES_INDEX:
        return schedules

    schedule_section = group_data[GROUP_SCHEDULES_INDEX]
    all_lista_spans = schedule_section.findall('.//span[@class="lista-elemento"]')

    for lista_span in all_lista_spans:
        nested_classroom = lista_span.findall('span[@class="lista-elemento"]')
        if not nested_classroom:
            continue

        schedule_span = lista_span.find("span")
        if schedule_span is None:
            continue

        schedule_txt = schedule_span.text_content()
        match = _SCHEDULE_REGEX.match(schedule_txt)
        if match is None:
            continue

        day, start_time, end_time = match.groups()
        classroom_container = lista_span.find("span[@class='lista-elemento']")
        classroom = classroom_container.text_content() if classroom_container is not None else None

        schedules.append(
            Schedule(
                day=day,
                start_time=start_time,
                end_time=end_time,
                classroom=classroom or "",
            )
        )

    return schedules


def _extract_spots(group_data: list[HtmlElement]) -> int | None:
    """Extract available spots from group data."""
    if len(group_data) < MIN_GROUP_DATA_LENGTH_WITH_SPOTS:
        return None

    spots_spans = group_data[GROUP_SPOTS_INDEX].findall(".//span")
    if not spots_spans:
        return None

    try:
        return int(spots_spans[-1].text_content().strip())
    except ValueError:
        return None


def _extract_group(group: HtmlElement, course_name: str, group_index: int = 0) -> Group | None:
    """Extract one group from a group container.

    ## Args
        group: HTML element containing group data.
        course_name: Name of the course for diagnostic context.
        group_index: Index of this group in the course for diagnostics.

    ## Returns
        Group dataclass or None if panel not found.
    """
    parent_group = group.parent
    group_name: str | None = None
    if parent_group is not None:
        h2_elem = parent_group.find("h2", class_="af_showDetailHeader_title-text0")
        if h2_elem is not None:
            group_name = h2_elem.text_content()

    panel_div = group.find("div", class_="af_panelGroupLayout")
    if panel_div is None:
        return None

    group_data = list(panel_div)
    if not group_data:
        return None

    actual_count = len(group_data)

    # Log structure deviations for debugging
    if actual_count < MIN_GROUP_DATA_LENGTH_WITH_SPOTS:
        logger.debug(
            "Group {} in course '{}' has {} divs (expected {} for full data). Fields: {}",
            group_index,
            course_name,
            actual_count,
            MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
            [d.text_content()[:30].strip() for d in group_data],
        )

    # Extract teacher with bounds checking and diagnostics
    if actual_count <= GROUP_TEACHER_INDEX:
        logger.warning(
            "Cannot extract teacher from group {} in course '{}': only {} divs present (expected at index {})",
            group_index,
            course_name,
            actual_count,
            GROUP_TEACHER_INDEX,
        )
        teacher = DEFAULT_TEACHER
    else:
        teacher_spans = group_data[GROUP_TEACHER_INDEX].findall(".//span")
        teacher = teacher_spans[-1].text_content() if teacher_spans else DEFAULT_TEACHER

    # Extract other fields with bounds checking
    faculty: str | None = (
        _extract_label_value(group_data[GROUP_FACULTY_INDEX])
        if len(group_data) > GROUP_FACULTY_INDEX
        else None
    )

    if faculty is None:
        logger.debug(
            "Faculty field missing in group {} of course '{}' (div count: {})",
            group_index,
            course_name,
            actual_count,
        )

    schedules = _extract_schedules(group_data)
    duration: str | None = (
        _extract_label_value(group_data[GROUP_DURATION_INDEX])
        if len(group_data) > GROUP_DURATION_INDEX
        else None
    )
    schedule_type: str | None = (
        _extract_label_value(group_data[GROUP_SCHEDULE_TYPE_INDEX])
        if len(group_data) > GROUP_SCHEDULE_TYPE_INDEX
        else None
    )
    spots = _extract_spots(group_data)

    if spots is None:
        logger.debug(
            "Spots info missing in group {} of course '{}' (div count: {})",
            group_index,
            course_name,
            actual_count,
        )

    return Group(
        group_name=group_name or DEFAULT_GROUP_NAME,
        teacher=teacher or DEFAULT_TEACHER,
        faculty=faculty or DEFAULT_FACULTY,
        course_name=course_name,
        schedules=schedules,
        duration=duration or DEFAULT_DURATION,
        schedule_type=schedule_type or DEFAULT_SCHEDULE_TYPE,
        spots=spots,
    )


def _extract_prereq_metadata(parser: HtmlParser) -> tuple[str, int, str]:
    """Extract basic course metadata required by prerequisites parser."""
    h2_elements = parser.find_all("h2")
    if not h2_elements:
        raise ValueError("Course name element not found in prerequisites XML")

    course_name = _safe_text_content(h2_elements[0])
    credits = _extract_credits(parser)
    typology = _extract_typology(parser)
    return course_name, credits, typology


def _extract_condition_values(condition_info_div: HtmlElement) -> list[str] | None:
    """Extract ordered condition fields from a condition info block."""
    condition_headers_spans = condition_info_div.css_select(
        "span.strong.af_panelGroupLayout > span.margin-l"
    )
    condition_values_spans = [header.getnext() for header in condition_headers_spans]

    if len(condition_headers_spans) != len(condition_values_spans):
        logger.warning(
            "Condition header/value count mismatch: {} headers, {} values",
            len(condition_headers_spans),
            len(condition_values_spans),
        )
        return None
    if len(condition_headers_spans) < REQUIRED_CONDITION_HEADERS:
        logger.warning(
            "Condition has only {} headers (expected {}): {}",
            len(condition_headers_spans),
            REQUIRED_CONDITION_HEADERS,
            [h.text_content() for h in condition_headers_spans],
        )
        return None

    return [
        _safe_text_content(condition_values_spans[0]),
        _safe_text_content(condition_values_spans[1]),
        _safe_text_content(condition_values_spans[2]),
        _safe_text_content(condition_values_spans[3]),
    ]


def _extract_prereqs_from_divs(condition_prereq_divs: list[HtmlElement]) -> list[Prerequisite]:
    """Extract prerequisite courses from prerequisite container divs."""
    prereqs: list[Prerequisite] = []
    for prereq_div in condition_prereq_divs:
        prereq_code_spans = prereq_div.css_select("span.af_panelGroupLayout > span")
        if not prereq_code_spans:
            continue

        prereq_code_span = prereq_code_spans[0]
        prereq_code = _safe_text_content(prereq_code_span)
        next_sibling = prereq_code_span.getnext()
        prereq_name = _safe_text_content(next_sibling)

        prereqs.append(Prerequisite(course_code=prereq_code, course_name=prereq_name))

    return prereqs


def _parse_condition(condition_div: HtmlElement) -> PrereqCondition | None:
    """Parse one prerequisite condition block into a validated model."""
    condition_sub_divs = list(condition_div)
    if len(condition_sub_divs) < 2:
        return None

    condition_values = _extract_condition_values(condition_sub_divs[0])
    if condition_values is None:
        return None

    prereqs = _extract_prereqs_from_divs(condition_sub_divs[1:])
    return PrereqCondition.model_validate(
        {
            "condition": condition_values[0],
            "type": condition_values[1],
            "all_required": condition_values[2],
            "number_of_courses": condition_values[3],
            "prerequisites": prereqs,
        }
    )


def scrape_info(xml: str) -> CourseInfo:
    """Parse comprehensive course information from Oracle ADF course detail page.

    ## Args
        xml: Raw XML/HTML from SIA course detail page response.

    ## Returns
        CourseInfo dataclass with complete course data including all groups and schedules.

    ## Raises
        ValueError: If course name or credits elements are not found in XML.
    """
    parser = HtmlParser(xml)

    course_name_elem = parser.find("h2")
    if course_name_elem is None:
        raise ValueError("Course name element not found in XML")
    course_name = course_name_elem.text_content()

    credits = _extract_credits(parser)
    typology = _extract_typology(parser)

    group_list: list[Group] = []
    available_spots = 0

    groups = parser.css_select(".af_showDetailHeader_content0")
    for idx, group in enumerate(groups):
        extracted_group = _extract_group(group, course_name, group_index=idx)
        if extracted_group is None:
            continue
        group_list.append(extracted_group)
        if extracted_group.spots is not None:
            available_spots += extracted_group.spots

    return CourseInfo(
        course_name=course_name,
        credits=credits,
        typology=typology,
        available_spots=available_spots,
        scrape_timestamp=format_date(datetime.now()),
        groups=group_list,
    )


def scrape_info_typed(xml: str) -> CourseInfoTyped:
    """Parse course information using Rust typed JSON contract.

    This function uses the Rust Phase 3 typed endpoint and validates the
    resulting payload with strict Pydantic models.

    Args:
        xml: Raw XML/HTML from SIA course detail page response.

    Returns:
        Strictly validated typed course payload.
    """
    typed_json = sia_scraper_rust.parse_course_info_json(xml)  # type: ignore[attr-defined]
    return CourseInfoTyped.model_validate_json(typed_json)


def scrape_prereqs(xml: str) -> CoursePrereqs:
    """Parse course prerequisites and enrollment conditions from Oracle ADF XML.

    ## Args
        xml: Raw XML/HTML from SIA course detail page response.

    ## Returns
        CoursePrereqs dataclass with course info and list of prerequisite conditions.

    ## Raises
        ValueError: If course name or credits elements are not found in XML.
    """
    parser = HtmlParser(xml)

    course_name, credits, typology = _extract_prereq_metadata(parser)

    conditions: list[PrereqCondition] = []

    condition_divs = parser.css_select(
        "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout"
    )

    for condition_div in condition_divs:
        condition = _parse_condition(condition_div)
        if condition is not None:
            conditions.append(condition)

    return CoursePrereqs(
        course_name=course_name,
        code=None,
        credits=credits,
        typology=typology,
        conditions=conditions,
    )
