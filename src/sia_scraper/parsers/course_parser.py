"""Course information and prerequisite parsing functions.

This module provides functions for extracting course data from Oracle ADF XML/HTML
responses returned by SIA's web interface.
"""

import re
from datetime import datetime
from typing import Any

from ..constants.business import (
    GROUP_DURATION_INDEX,
    GROUP_FACULTY_INDEX,
    GROUP_SCHEDULE_TYPE_INDEX,
    GROUP_SCHEDULES_INDEX,
    GROUP_SPOTS_INDEX,
    GROUP_TEACHER_INDEX,
    MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
)
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

_SCHEDULE_REGEX = re.compile(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})")


def get_plain_text(xml: str) -> str:
    """Extract human-readable plain text from Oracle ADF XML response.

    ## Args
        xml: Raw XML/HTML from SIA Oracle ADF response.

    ## Returns
        Plain text content before the first triple non-breaking space separator.
    """
    from sia_scraper_rust import get_plain_text as rust_get_plain_text

    return rust_get_plain_text(xml)


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
        raise ValueError("Credits element not found in XML")
    credits_spans = credits_elem.findall(".//span")
    if not credits_spans:
        raise ValueError("Credits span not found in XML")
    return int(credits_spans[-1].text_content().strip())


def _extract_typology(parser: HtmlParser) -> str:
    """Extract typology from course XML.

    ## Args
        parser: HtmlParser instance with course XML loaded.

    ## Returns
        Course typology string, or "Unknown" if not found.
    """
    tipology_elem = parser.find("span", class_="detass-tipologia")
    if tipology_elem is None:
        return "Unknown"
    tipology_spans = tipology_elem.findall(".//span")
    if not tipology_spans:
        return "Unknown"
    return _safe_text_content(tipology_spans[-1], fallback="Unknown")


def _safe_text_content(element: Any, fallback: str = "") -> str:
    """Safely extract text content from an element, ensuring a string return."""
    if element is None:
        return fallback
    try:
        text = element.text_content()
        return str(text).strip() if text else fallback
    except (AttributeError, TypeError):
        return fallback


def _extract_label_value(item: HtmlElement, fallback: str = "Unknown") -> str:
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


def _extract_group(group: HtmlElement, course_name: str) -> Group | None:
    """Extract one group from a group container."""
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

    teacher_spans = group_data[GROUP_TEACHER_INDEX].findall(".//span")
    teacher: str | None = teacher_spans[-1].text_content() if teacher_spans else None
    faculty: str | None = (
        _extract_label_value(group_data[GROUP_FACULTY_INDEX])
        if len(group_data) > GROUP_FACULTY_INDEX
        else None
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

    return Group(
        group_name=group_name or "",
        teacher=teacher or "",
        faculty=faculty or "",
        course_name=course_name,
        schedules=schedules,
        duration=duration or "",
        schedule_type=schedule_type or "",
        spots=spots,
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
    for group in groups:
        extracted_group = _extract_group(group, course_name)
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

    h2_elements = parser.find_all("h2")
    if not h2_elements:
        raise ValueError("Course name element not found in prerequisites XML")
    course_name = _safe_text_content(h2_elements[0])

    credits = _extract_credits(parser)

    tipology_elements = parser.find_all("span", class_="detass-tipologia")
    typology: str | None = tipology_elements[0].text_content() if tipology_elements else None

    conditions: list[PrereqCondition] = []

    condition_divs = parser.css_select(
        "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout"
    )

    for condition_div in condition_divs:
        condition_sub_divs = list(condition_div)
        if len(condition_sub_divs) < 2:
            continue

        condition_info_div = condition_sub_divs[0]
        condition_headers_spans = condition_info_div.css_select(
            "span.strong.af_panelGroupLayout > span.margin-l"
        )
        condition_values_spans = [header.getnext() for header in condition_headers_spans]

        if len(condition_headers_spans) != len(condition_values_spans):
            continue
        if len(condition_headers_spans) < 4:
            continue

        prereq_values = [
            _safe_text_content(condition_values_spans[0]),
            _safe_text_content(condition_values_spans[1]),
            _safe_text_content(condition_values_spans[2]),
            _safe_text_content(condition_values_spans[3]),
        ]

        prereqs: list[Prerequisite] = []
        condition_prereq_divs = condition_sub_divs[1:]

        for prereq_div in condition_prereq_divs:
            prereq_code_spans = prereq_div.css_select("span.af_panelGroupLayout > span")
            if not prereq_code_spans:
                continue

            prereq_code_span = prereq_code_spans[0]
            prereq_code = _safe_text_content(prereq_code_span)
            next_sibling = prereq_code_span.getnext()
            prereq_name = _safe_text_content(next_sibling)

            prereqs.append(Prerequisite(course_code=prereq_code, course_name=prereq_name))

        conditions.append(
            PrereqCondition.model_validate(
                {
                    "condition": prereq_values[0],
                    "type": prereq_values[1],
                    "all_required": prereq_values[2],
                    "number_of_courses": prereq_values[3],
                    "prerequisites": prereqs,
                }
            )
        )

    return CoursePrereqs(
        course_name=course_name,
        code=None,
        credits=credits,
        typology=typology or "",
        conditions=conditions,
    )
