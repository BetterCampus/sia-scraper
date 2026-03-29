"""SIA Scraper Orchestrator Module.

This module provides the high-level orchestration layer for scraping course data from
Universidad Nacional de Colombia's SIA (Sistema de Información Académica) system.

The SiaScraper class acts as a facade over SiaSession, delegating session management
and HTTP operations to SiaSession while handling all XML parsing and data extraction:
- Course information (name, credits, typology, groups)
- Schedule data (days, times, classrooms)
- Group details (teacher, faculty, spots, duration)
- Prerequisites and conditions

Architecture:
    SiaScraper (this module) - Orchestration, delegation to SiaSession
        ↓ delegates to
    SiaSession - HTTP requests, Oracle ADF state management, navigation
        ↓ uses
    parsers - Course info and prerequisites extraction with dataclasses
        ↓ uses
    constants - Oracle ADF component IDs, request templates, status enums
"""

from typing import Any

from .constants import http, status
from .exceptions import SiaSessionException
from .parsers import CourseInfo, CoursePrereqs, scrape_info, scrape_prereqs
from .session import SiaSession


class SiaScraper:
    """High-level facade for SIA course data scraping.

    This class provides a simplified interface for scraping course information from SIA
    by delegating session management to SiaSession and handling all XML parsing logic.

    The scraper maintains career context (code, name, course list) and provides methods
    to extract course details, schedules, groups, and prerequisites from Oracle ADF XML.

    ## Typical Workflow
        1. Create scraper: sc = SiaScraper()
        2. Set career: sc.set_career("0-2-8-3")
        3. Scrape courses: course_info = sc.get_course_info(course_code="2016489")
        4. Access data: course_info.groups[0].schedules
    """

    def __init__(
        self,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | None = None,
        init_session: bool = True,
    ) -> None:
        """Initialize SiaScraper with optional session restoration.

        ## Args
            timeout: HTTP request timeout in seconds for SIA operations.
            session_data: Serialized session state from get_session_data().
                If provided, restores previous session (career, course list, cookies).
            init_session: Whether to initialize a new HTTP session if session_data
                is empty. Set to False to defer session creation.

        ## Note
            Session restoration is used to avoid re-authenticating and re-navigating
            through SIA's multi-page workflow when session_data is available.
        """
        if session_data is None:
            session_data = {}

        self.__sia_session = SiaSession(
            timeout=timeout, session_data=session_data, init_session=init_session
        )

    @property
    def career_name(self) -> str:
        """Human-readable name of the current academic program."""
        value = self.__sia_session.career_name
        return value if isinstance(value, str) else "N/A"

    @property
    def career_code(self) -> str:
        """Search code identifier for the current career (e.g., "0-2-8-3")."""
        value = self.__sia_session.career_code
        return value if isinstance(value, str) else ""

    @property
    def course_list(self) -> list[dict[str, str]]:
        """List of course codes available in the current career."""
        value = self.__sia_session.course_list
        return value if isinstance(value, list) else []

    @property
    def sia_session(self) -> SiaSession:
        """Underlying SiaSession instance for direct access to session operations."""
        return self.__sia_session

    ##################### PUBLIC METHODS #####################

    def create_session(self) -> "SiaScraper":
        """Initialize a new HTTP session with SIA's Oracle ADF backend.

        ## Returns
            Self for method chaining.

        ## Raises
            SiaSessionException.TimeoutError: If SIA server is unreachable.
        """
        self.__sia_session.init_session()
        return self

    def load_session(self, session_data: dict[str, Any]) -> "SiaScraper":
        """Restore a previously saved session from serialized state.

        ## Args
            session_data: Serialized session obtained from get_session_data().
                Contains cookies, Oracle ADF state tokens, career context.

        ## Returns
            Self for method chaining.

        """
        self.__sia_session.load_session(session_data)
        return self

    def get_session_data(self) -> dict:
        """Serialize current session state for later restoration.

        ## Returns
            Dictionary containing session cookies, Oracle ADF tokens, and career context.
            Can be passed to load_session() to restore the session.

        ## Note
            Useful for persisting sessions across requests (e.g., in Flask session storage).
        """
        return self.__sia_session.get_session_data()

    def close_session(self) -> "SiaScraper":
        """Close the HTTP session and release resources.

        ## Returns
            Self for method chaining.
        """
        self.__sia_session.close_session()
        return self

    def valid_session(self) -> bool:
        """Check if the current session is still valid for SIA operations.

        ## Returns
            True if session has valid Oracle ADF tokens and is in a navigable state.
            False if session needs to be reinitialized.
        """
        return self.__sia_session.valid_session()

    def set_career(self, search_code: str, electives: bool = False) -> "SiaScraper":
        """Navigate to a specific academic program and load its course list.

        ## Args
            search_code: Career search code from SIA (e.g., "0-2-8-3" for Computer Science).
                Format: "{study_level}-{campus}-{faculty}-{career_index}"
            electives: If True, navigate to elective courses page instead of core curriculum.

        ## Returns
            Self for method chaining.

        ## Raises
            SiaSessionException.SessionNotSet: If session not initialized.
            SiaSessionException.TimeoutError: If SIA server doesn't respond.

        """
        self.__sia_session.set_career(search_code, electives=electives)
        return self

    def get_course_info(self, course_index: int = 0, course_code: str = "") -> CourseInfo:
        """Retrieve complete course information including all groups and schedules.

        ## Args
            course_index: Zero-based index in current career's course list.
                Ignored if course_code is provided.
            course_code: Course code to search for (e.g., "2016489").
                If provided, overrides course_index.

        ## Returns
            CourseInfo dataclass with structure:
                - course_name: str
                - credits: int
                - typology: str
                - available_spots: int
                - scrape_timestamp: str
                - groups: list[Group]
                    - group_name, teacher, faculty, course_name
                    - schedules: list[Schedule] (day, start_time, end_time, classroom)
                    - duration, schedule_type, spots

        ## Raises
            ValueError: If course name, credits, or tipology elements not found in XML.
            SiaSessionException.InvalidStatus: If session not on career/course page.
            ValueError: If course code is not found in the current course list.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return scrape_info(xml)

    def get_course_index(self, course_code: str) -> int:
        """Find the index of a course code in the current career's course list.

        ## Args
            course_code: Course code to search for (e.g., "2016489").

        ## Returns
            Zero-based index if found.

        ## Raises
            SiaSessionException.InvalidStatus: If session not on career or course page.
            ValueError: If course code is not found in the current course list.

        ## Note
            The historical 0/1 swap workaround was removed after ViewState auto-sync.
            Validate behavior against live SIA if index mismatches are observed.
        """
        if self.__sia_session.STATUS not in (
            status.SiaSessionStatus.ON_CAREER_PAGE,
            status.SiaSessionStatus.ON_COURSE_PAGE,
        ):
            raise SiaSessionException.InvalidStatus from None

        for i, course in enumerate(self.course_list):
            if course_code in course:
                return i
        raise ValueError(f"Course code '{course_code}' not found")

    def get_course_prereqs(self, course_index: int = 0, course_code: str = "") -> CoursePrereqs:
        """Retrieve course prerequisites and enrollment conditions.

        ## Args
            course_index: Zero-based index in current career's course list.
                Ignored if course_code is provided.
            course_code: Course code to search for (e.g., "2016489").
                If provided, overrides course_index.

        ## Returns
            CoursePrereqs dataclass with structure:
                - course_name: str
                - code: str
                - credits: int
                - typology: str
                - conditions: list[PrereqCondition]
                    - condition, type, all_required, number_of_courses
                        - prerequisites: list[Prerequisite]
                            - course_code, course_name

        ## Raises
            SiaSessionException.InvalidStatus: If session not on career/course page.
            ValueError: If course code is not found in the current course list.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return scrape_prereqs(xml)

    def scrape_courses(
        self, courses_indices: list[int] | None = None, courses_codes: list[str] | None = None
    ) -> list[CourseInfo]:
        """Batch scrape multiple courses by index or code.

        ## Args
            courses_indices: List of zero-based indices in course list.
                If empty, derives from courses_codes.
            courses_codes: List of course codes to scrape.
                Used to populate courses_indices if that is empty.

        ## Returns
            List of CourseInfo dataclasses with code field populated.

        ## Note
            Sorts indices before scraping for more efficient sequential access.
        """
        if courses_indices is None:
            courses_indices = []
        if courses_codes is None:
            courses_codes = []

        if courses_indices == []:
            courses_indices = [self.get_course_index(course_code) for course_code in courses_codes]

        courses_indices.sort()
        courses = [self.get_course_info(course_index) for course_index in courses_indices]

        for i, course in enumerate(courses):
            course.code = courses_codes[i]

        return courses


def init_sia_scraper(
    search_code: str,
    is_electives: bool,
    session_data: dict[str, Any] | None = None,
    timeout: int = http.DEFAULT_TIMEOUT,
) -> SiaScraper:
    """Initialize or restore a SiaScraper with intelligent session management.

    This factory function handles three scenarios:
    1. No session_data: Creates new session and navigates to career
    2. Valid session_data: Restores session and reuses it
    3. Invalid/expired session: Falls back to creating new session

    ## Args
        search_code: Career search code (e.g., "0-2-8-3").
        is_electives: Whether to navigate to electives page.
        session_data: Optional serialized session from get_session_data().
        timeout: HTTP request timeout in seconds.

    ## Returns
        SiaScraper instance ready for scraping the specified career.

    ## Note
        If the career in session_data differs from search_code, automatically
        navigates to the new career while preserving the session.

    ## Warning
        Session validation may have false negatives.
        If session appears invalid, falls back to creating new session.
    """
    if session_data is None:
        session_data = {}

    if session_data == {}:
        return create_career_session(search_code, is_electives, timeout=timeout)

    sc = SiaScraper(timeout=timeout, session_data=session_data)

    if not sc.valid_session():
        return create_career_session(search_code, is_electives, timeout=timeout)

    if sc.career_code != search_code or sc.sia_session.is_electives != is_electives:
        sc.set_career(search_code, electives=is_electives)

    return sc


def create_career_session(
    search_code: str, is_electives: bool, timeout: int = http.DEFAULT_TIMEOUT
) -> SiaScraper:
    """Create a new SiaScraper with a fresh session and navigate to career.

    ## Args
        search_code: Career search code (e.g., "0-2-8-3").
        is_electives: Whether to navigate to electives page.
        timeout: HTTP request timeout in seconds.

    ## Returns
        SiaScraper instance with new session, positioned at career page.
    """
    sc = SiaScraper(timeout=timeout)
    sc.set_career(search_code, electives=is_electives)
    return sc
