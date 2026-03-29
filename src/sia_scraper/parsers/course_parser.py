"""Course information and prerequisite parsing functions.

This module provides functions for extracting course data from Oracle ADF XML/HTML
responses returned by SIA's web interface.
"""

import re
from datetime import datetime
from typing import TypeVar

from ..date_formatter import DateFormatter
from .html_parser import HtmlParser
from .models import (
    CourseInfo,
    CoursePrereqs,
    Group,
    PrereqCondition,
    Prerequisite,
    Schedule,
)

T = TypeVar("T")


def get_plain_text(xml: str) -> str:
    """Extract human-readable plain text from Oracle ADF XML response.

    ## Args
        xml: Raw XML/HTML from SIA Oracle ADF response.

    ## Returns
        Plain text content before the first triple non-breaking space separator.

    ## Note
        Oracle ADF uses \\xa0\\xa0\\xa0 as a visual separator in rendered text.
        This method extracts only the primary content before that separator.
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


def scrape_info(xml: str) -> CourseInfo:
    """Parse comprehensive course information from Oracle ADF course detail page.

    This function extracts course metadata and ALL group details (schedules, teachers,
    spots, etc.) from the XML/HTML response of a course detail page.

    ## Args
        xml: Raw XML/HTML from SIA course detail page response.

    ## Returns
        CourseInfo dataclass with complete course data including all groups and schedules.

    ## Oracle ADF XML Structure
        ```html
        <h2>                                    → Course name
        <span class="detass-creditos">          → Credits (nested span)
        <span class="detass-tipologia">         → Tipology (nested span)
        <div class="af_showDetailHeader_content0">  → Each group container
            <h2 class="af_showDetailHeader_title-text0">  → Group name
            <div class="af_panelGroupLayout">   → Group data container
                [0] <span><span>                → Teacher name
                [1] <span><span>                → Faculty
                [2] <span><span>                → Schedules (lista-elemento)
                [3] <span><span>                → Duration
                [4] <span><span>                → Jornada (schedule type)
                [5] <span><span>                → Spots (optional)
        ```

    ## Raises
        ValueError: If course name, credits, or tipology elements not found in XML.
    """
    parser = HtmlParser(xml)

    course_name_elem = parser.find("h2")
    if course_name_elem is None:
        raise ValueError("Course name element not found in XML")
    course_name = course_name_elem.text_content()

    credits = _extract_credits(parser)
    tipology = _extract_typology(parser)

    group_list: list[Group] = []
    available_spots = 0

    groups = parser.css_select(".af_showDetailHeader_content0")

    for group in groups:
        group_obj: dict = {}

        parent_group = group.parent
        if parent_group is not None:
            h2_elem = parent_group.find("h2", class_="af_showDetailHeader_title-text0")
            group_obj["groupName"] = (
                h2_elem.text_content().strip() if h2_elem is not None else "Unknown"
            )
        else:
            group_obj["groupName"] = "Unknown"

        panel_div = group.find("div", class_="af_panelGroupLayout")
        if panel_div is None:
            continue
        group_data = list(panel_div)

        if len(group_data) == 0:
            continue

        teacher_spans = group_data[0].findall(".//span")
        if teacher_spans:
            group_obj["teacher"] = teacher_spans[-1].text_content().strip()
        else:
            group_obj["teacher"] = "Not reported"

        faculty_spans = group_data[1].findall(".//span") if len(group_data) > 1 else []
        if faculty_spans:
            group_obj["faculty"] = faculty_spans[-1].text_content().strip()
        else:
            group_obj["faculty"] = "Unknown"
        group_obj["courseName"] = course_name

        schedules: list[Schedule] = []

        if len(group_data) > 2:
            schedule_section = group_data[2]
            all_lista_spans = schedule_section.findall('.//span[@class="lista-elemento"]')

            for lista_span in all_lista_spans:
                nested_classroom = lista_span.findall('span[@class="lista-elemento"]')
                if not nested_classroom:
                    continue

                schedule_span = lista_span.find("span")
                if schedule_span is None:
                    continue
                schedule_txt = schedule_span.text_content()

                match = re.match(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})", schedule_txt)
                if match is None:
                    continue
                day, start_time, end_time = match.groups()

                classroom_container = lista_span.find("span[@class='lista-elemento']")
                classroom = (
                    classroom_container.text_content().strip()
                    if classroom_container is not None
                    else ""
                )

                schedules.append(
                    Schedule(day=day, startTime=start_time, endTime=end_time, classroom=classroom)
                )

        group_obj["schedules"] = schedules

        if len(group_data) > 3:
            duration_spans = group_data[3].findall(".//span")
            group_obj["duration"] = (
                duration_spans[-1].text_content().strip() if duration_spans else "Unknown"
            )
        else:
            group_obj["duration"] = "Unknown"

        if len(group_data) > 4:
            schedule_type_spans = group_data[4].findall(".//span")
            group_obj["scheduleType"] = (
                schedule_type_spans[-1].text_content().strip() if schedule_type_spans else "Unknown"
            )
        else:
            group_obj["scheduleType"] = "Unknown"

        if len(group_data) < 6:
            group_obj["spots"] = "NaN"
        else:
            spots_spans = group_data[5].findall(".//span")
            if spots_spans:
                try:
                    spots = int(spots_spans[-1].text_content().strip())
                    group_obj["spots"] = spots
                    available_spots += spots
                except ValueError:
                    group_obj["spots"] = "NaN"
            else:
                group_obj["spots"] = "NaN"

        group_list.append(
            Group(
                groupName=group_obj["groupName"],
                teacher=group_obj["teacher"],
                faculty=group_obj["faculty"],
                courseName=group_obj["courseName"],
                schedules=group_obj["schedules"],
                duration=group_obj["duration"],
                scheduleType=group_obj["scheduleType"],
                spots=group_obj["spots"],
            )
        )

    return CourseInfo(
        courseName=course_name,
        credits=credits,
        typology=tipology,
        availableSpots=available_spots,
        scrapeTimestamp=DateFormatter(datetime.now()).format_date(),
        groups=group_list,
    )


def scrape_prereqs(xml: str) -> CoursePrereqs:
    """Parse course prerequisites and enrollment conditions from Oracle ADF XML.

    Extracts prerequisite courses organized by condition types (e.g., "Must pass ALL",
    "Must pass 2 of the following"). Each condition has metadata and a list of
    prerequisite course codes.

    ## Args
        xml: Raw XML/HTML from SIA course detail page response.

    ## Returns
        CoursePrereqs dataclass with course info and list of prerequisite conditions.

    ## Oracle ADF XML Structure
        ```html
        <h2>                                    → Course name (with code in parens)
        <span class="detass-creditos">          → Credits
        <span class="detass-tipologia">         → "Tipología: VALUE"
        <span class="borde salto af_panelGroupLayout">  → Condition containers
            <div class="margin-t af_panelGroupLayout">  → Each condition block
                [0] <div> Condition metadata    → Headers + values as siblings
                [1+] <div> Prerequisite courses → Code + name as siblings
        ```

    ## Raises
        ValueError: If course name or credits elements not found in XML.
    """
    parser = HtmlParser(xml)

    h2_elements = parser.find_all("h2")
    if not h2_elements:
        raise ValueError("Course name element not found in prerequisites XML")
    course_name = h2_elements[0].text_content()

    credits = _extract_credits(parser)

    course_code = course_name[course_name.index("(") + 1 : course_name.index(")")]

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

        prereq_info = {
            condition_headers_spans[0].text_content(): (
                condition_values_spans[0].text_content().strip()
                if condition_values_spans[0] is not None
                else ""
            ),
            condition_headers_spans[1].text_content(): (
                condition_values_spans[1].text_content().strip()
                if len(condition_values_spans) > 1 and condition_values_spans[1] is not None
                else ""
            ),
            condition_headers_spans[2].text_content(): (
                condition_values_spans[2].text_content().strip()
                if len(condition_values_spans) > 2 and condition_values_spans[2] is not None
                else ""
            ),
            condition_headers_spans[3].text_content(): (
                condition_values_spans[3].text_content().strip()
                if len(condition_values_spans) > 3 and condition_values_spans[3] is not None
                else ""
            ),
        }

        prereqs: list[Prerequisite] = []

        condition_prereqs_divs = condition_sub_divs[1:]

        for prereq_div in condition_prereqs_divs:
            prereq_code_spans = prereq_div.css_select("span.af_panelGroupLayout > span")
            if not prereq_code_spans:
                continue
            prereq_code_span = prereq_code_spans[0]
            prereq_code = prereq_code_span.text_content()

            next_sibling = prereq_code_span.getnext()
            prereq_name = next_sibling.text_content().strip() if next_sibling is not None else ""

            prereqs.append(
                Prerequisite(
                    course_code=prereq_code,
                    course_name=prereq_name,
                )
            )

        conditions.append(
            PrereqCondition(
                condition=list(prereq_info.values())[0] if prereq_info else "",
                type=list(prereq_info.values())[1] if len(prereq_info) > 1 else "",
                all_required=list(prereq_info.values())[2] if len(prereq_info) > 2 else "",
                number_of_courses=list(prereq_info.values())[3] if len(prereq_info) > 3 else "",
                prerequisites=prereqs,
            )
        )

    return CoursePrereqs(
        courseName=course_name,
        code=course_code,
        credits=credits,
        typology=typology,
        conditions=conditions,
    )
