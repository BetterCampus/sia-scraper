"""Course information and prerequisite parsing functions.

This module provides functions for extracting course data from Oracle ADF XML/HTML
responses returned by SIA's web interface.
"""

import re
from datetime import datetime

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
    parser = HtmlParser(xml)
    return parser.text_content().split("\xa0\xa0\xa0")[0]


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
    return tipology_spans[-1].text_content().strip()


def _extract_label_value(item: HtmlElement) -> str:
    spans = item.findall(".//span")
    if not spans:
        return "Unknown"
    return spans[-1].text_content().strip()


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
        classroom = (
            classroom_container.text_content().strip() if classroom_container is not None else ""
        )

        schedules.append(
            Schedule(
                day=day,
                start_time=start_time,
                end_time=end_time,
                classroom=classroom,
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
    if parent_group is not None:
        h2_elem = parent_group.find("h2", class_="af_showDetailHeader_title-text0")
        group_name = h2_elem.text_content().strip() if h2_elem is not None else "Unknown"
    else:
        group_name = "Unknown"

    panel_div = group.find("div", class_="af_panelGroupLayout")
    if panel_div is None:
        return None

    group_data = list(panel_div)
    if not group_data:
        return None

    teacher_spans = group_data[GROUP_TEACHER_INDEX].findall(".//span")
    teacher = teacher_spans[-1].text_content().strip() if teacher_spans else "Not reported"
    faculty = (
        _extract_label_value(group_data[GROUP_FACULTY_INDEX])
        if len(group_data) > GROUP_FACULTY_INDEX
        else "Unknown"
    )
    schedules = _extract_schedules(group_data)
    duration = (
        _extract_label_value(group_data[GROUP_DURATION_INDEX])
        if len(group_data) > GROUP_DURATION_INDEX
        else "Unknown"
    )
    schedule_type = (
        _extract_label_value(group_data[GROUP_SCHEDULE_TYPE_INDEX])
        if len(group_data) > GROUP_SCHEDULE_TYPE_INDEX
        else "Unknown"
    )
    spots = _extract_spots(group_data)

    return Group(
        group_name=group_name,
        teacher=teacher,
        faculty=faculty,
        course_name=course_name,
        schedules=schedules,
        duration=duration,
        schedule_type=schedule_type,
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
    course_name = h2_elements[0].text_content()

    credits = _extract_credits(parser)

    match = re.search(r"\((\d+)\)$", course_name.strip())
    course_code = match.group(1) if match else ""

    tipology_elements = parser.find_all("span", class_="detass-tipologia")
    if tipology_elements:
        typology = tipology_elements[0].text_content().split(": ")[-1]
    else:
        typology = "Unknown"

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
            condition_values_spans[0].text_content().strip() if condition_values_spans[0] else "",
            condition_values_spans[1].text_content().strip() if condition_values_spans[1] else "",
            condition_values_spans[2].text_content().strip() if condition_values_spans[2] else "",
            condition_values_spans[3].text_content().strip() if condition_values_spans[3] else "",
        ]

        prereqs: list[Prerequisite] = []
        condition_prereq_divs = condition_sub_divs[1:]

        for prereq_div in condition_prereq_divs:
            prereq_code_spans = prereq_div.css_select("span.af_panelGroupLayout > span")
            if not prereq_code_spans:
                continue

            prereq_code_span = prereq_code_spans[0]
            prereq_code = prereq_code_span.text_content()
            next_sibling = prereq_code_span.getnext()
            prereq_name = next_sibling.text_content().strip() if next_sibling is not None else ""

            prereqs.append(Prerequisite(course_code=prereq_code, course_name=prereq_name))

        conditions.append(
            PrereqCondition(
                condition=prereq_values[0],
                type=prereq_values[1],
                all_required=prereq_values[2],
                number_of_courses=prereq_values[3],
                prerequisites=prereqs,
            )
        )

    return CoursePrereqs(
        course_name=course_name,
        code=course_code,
        credits=credits,
        typology=typology,
        conditions=conditions,
    )
