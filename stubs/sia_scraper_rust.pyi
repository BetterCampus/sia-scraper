"""Type stubs for sia_scraper_rust PyO3 extension module."""

from collections.abc import Awaitable
from typing import Any

class SiaScraperException(Exception): ...

class ScheduleModel:
    day: str
    start_time: str
    end_time: str
    classroom: str

    def __init__(self, day: str, start_time: str, end_time: str, classroom: str) -> None: ...

class GroupModel:
    group_name: str
    teacher: str
    faculty: str
    course_name: str
    schedules: list[ScheduleModel]
    duration: str
    schedule_type: str
    spots: int | None
    code: str | None

    def __init__(
        self,
        group_name: str,
        teacher: str,
        faculty: str,
        course_name: str,
        schedules: list[ScheduleModel],
        duration: str,
        schedule_type: str,
        spots: int | None,
        code: str | None,
    ) -> None: ...

class CourseInfoModel:
    course_name: str
    credits: int
    typology: str
    available_spots: int
    scrape_timestamp: str
    groups: list[GroupModel]
    code: str | None

    def __init__(
        self,
        course_name: str,
        credits: int,
        typology: str,
        available_spots: int,
        scrape_timestamp: str,
        groups: list[GroupModel],
        code: str | None,
    ) -> None: ...

class CourseListEntryModel:
    course_code: str
    course_name: str

    def __init__(self, course_code: str, course_name: str) -> None: ...

class SessionStateModel:
    session_headers: dict[str, str]
    session_cookies: dict[str, str]
    params: dict[str, str]
    javax_faces_view_state: str | None
    career_code: str
    career_name: str
    is_electives: bool
    status: str
    course_list: list[CourseListEntryModel]

    def __init__(
        self,
        session_headers: dict[str, str],
        session_cookies: dict[str, str],
        params: dict[str, str],
        career_code: str,
        career_name: str,
        is_electives: bool,
        status: str,
        course_list: list[CourseListEntryModel],
        javax_faces_view_state: str | None = None,
    ) -> None: ...

class PrerequisiteModel:
    course_code: str
    course_name: str

    def __init__(self, course_code: str, course_name: str) -> None: ...

class PrereqConditionModel:
    condition: int
    prereq_type: str
    all_required: bool
    number_of_courses: int
    prerequisites: list[PrerequisiteModel]

    def __init__(
        self,
        condition: int,
        prereq_type: str,
        all_required: bool,
        number_of_courses: int,
        prerequisites: list[PrerequisiteModel],
    ) -> None: ...

class CoursePrereqsModel:
    course_name: str
    code: str | None
    credits: int
    typology: str
    conditions: list[PrereqConditionModel]

    def __init__(
        self,
        course_name: str,
        credits: int,
        typology: str,
        conditions: list[PrereqConditionModel],
        code: str | None = None,
    ) -> None: ...

def parse_course_info(xml: str) -> CourseInfoModel: ...
def parse_course_info_json(xml: str) -> str: ...
def extract_view_state(html: str) -> str: ...
def parse_prereqs(xml: str) -> CoursePrereqsModel: ...
def parse_prereqs_json(xml: str) -> str: ...
def get_course_list(html: str | bytes) -> list[dict[str, str]]: ...
def get_plain_text(xml: str) -> str: ...
def init_oracle_adf_request_dict(
    tipology_index: str,
    window_id: str | None = None,
    page_id: str | None = None,
    view_state: str | None = None,
) -> dict[str, Any]: ...
def build_oracle_adf_request_body(
    request_dict: dict[str, Any],
    data_name: str,
    idx: int,
    career_indices: list[str],
    course_list_len: int,
) -> dict[str, Any]: ...
def get_oracle_adf_event_dict(
    id: str,
    event_type: str,
    idx: int,
) -> dict[str, Any]: ...
def async_get(url: str) -> Any: ...
def async_post(url: str, body: str) -> Any: ...
def async_get_with_config(
    url: str,
    timeout: int | None = None,
    user_agent: str | None = None,
) -> Any: ...
def init_sia_session(timeout: int | None = None) -> Awaitable[SessionStateModel]: ...
def init_sia_session_json(timeout: int | None = None) -> Any: ...
def set_career(
    timeout: int | None = None,
    search_code: str = "",
    electives: bool | None = None,
) -> Awaitable[SessionStateModel]: ...
def set_career_json(
    timeout: int | None = None,
    search_code: str = "",
    electives: bool | None = None,
) -> Any: ...
def get_course_xml(
    timeout: int | None = None,
    course_index: int = 0,
    career_indices: list[str] | None = None,
    electives: bool | None = None,
) -> Any: ...
