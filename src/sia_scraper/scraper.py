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
        self.__career_name = "N/A"
        self.__career_code = ""
        self.__course_list: list[dict[str, str]] = []

        if session_data is None:
            session_data = {}

        self.__sia_session = SiaSession(
            timeout=timeout, session_data=session_data, init_session=init_session
        )

        if session_data:
            if self.__sia_session.career_code != "":
                self.__career_code = self.__sia_session.career_code
                self.__career_name = self.__sia_session.career_name
                self.__course_list = self.__sia_session.course_list

    @property
    def career_name(self) -> str:
        """Human-readable name of the current academic program."""
        return self.__career_name

    @property
    def career_code(self) -> str:
        """Search code identifier for the current career (e.g., "0-2-8-3")."""
        return self.__career_code

    @property
    def course_list(self) -> list[dict[str, str]]:
        """List of course codes available in the current career."""
        return self.__course_list

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

    def load_session(self, session_data: dict) -> "SiaScraper":
        """Restore a previously saved session from serialized state.

        ## Args
            session_data: Serialized session obtained from get_session_data().
                Contains cookies, Oracle ADF state tokens, career context.

        ## Returns
            Self for method chaining.

        ## Note
            If the session contains career data, synchronizes local career attributes
            (__career_code, __career_name, __course_list) with session state.
        """
        self.__sia_session.load_session(session_data)
        if self.__sia_session.career_code != "":
            self.__career_code = self.__sia_session.career_code
            self.__career_name = self.__sia_session.career_name
            self.__course_list = self.__sia_session.course_list
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

        ## Note
            Updates internal career context: __career_code, __career_name, __course_list.
        """
        self.__sia_session.set_career(search_code, electives=electives)
        self.__career_code = self.__sia_session.career_code
        self.__course_list = self.__sia_session.course_list
        self.__career_name = self.__sia_session.career_name
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
                - courseName: str
                - credits: int
                - typology: str
                - availableSpots: int
                - scrapeTimestamp: str
                - groups: list[Group]
                    - groupName, teacher, faculty, courseName
                    - schedules: list[Schedule] (day, startTime, endTime, classroom)
                    - duration, scheduleType, spots

        ## Raises
            ValueError: If course name, credits, or tipology elements not found in XML.
            AssertionError: If session not on career/course page.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return scrape_info(xml)

    def get_course_index(self, course_code: str) -> int:
        """Find the index of a course code in the current career's course list.

        ## Args
            course_code: Course code to search for (e.g., "2016489").

        ## Returns
            Zero-based index if found, -1 if not found.

        ## Raises
            AssertionError: If session not on career or course page.

        ## Note
            SIA's Oracle ADF table returns indices 0 and 1 in swapped order in its internal
            state (though the course list order is correct). This function applies the
            necessary correction when looking up indices.
        """
        assert self.__sia_session.STATUS in (
            status.SiaSessionStatus.ON_CAREER_PAGE,
            status.SiaSessionStatus.ON_COURSE_PAGE,
        ), "Session not on career page or course page, can't get course index"

        for i, course in enumerate(self.__course_list):
            if course_code in course:
                if i == 0 or i == 1:
                    return (i + 1) % 2  # Swap: 0→1, 1→0
                return i
        return -1

    def get_course_prereqs(self, course_index: int = 0, course_code: str = "") -> CoursePrereqs:
        """Retrieve course prerequisites and enrollment conditions.

        ## Args
            course_index: Zero-based index in current career's course list.
                Ignored if course_code is provided.
            course_code: Course code to search for (e.g., "2016489").
                If provided, overrides course_index.

        ## Returns
            CoursePrereqs dataclass with structure:
                - courseName: str
                - code: str
                - credits: int
                - typology: str
                - conditions: list[PrereqCondition]
                    - condition, type, all_required, number_of_courses
                    - prerequisites: list[Prerequisite]
                        - course_code, course_name

        ## Raises
            AssertionError: If session not on career/course page.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return scrape_prereqs(xml)

    def scrape_courses(
        self, courses_indexs: list[int] | None = None, courses_codes: list[str] | None = None
    ) -> list[CourseInfo]:
        """Batch scrape multiple courses by index or code.

        ## Args
            courses_indexs: List of zero-based indices in course list.
                If empty, derives from courses_codes.
            courses_codes: List of course codes to scrape.
                Used to populate courses_indexs if that is empty.

        ## Returns
            List of CourseInfo dataclasses with code field populated.

        ## Note
            Sorts indices before scraping for more efficient sequential access.
        """
        if courses_indexs is None:
            courses_indexs = []
        if courses_codes is None:
            courses_codes = []

        if courses_indexs == []:
            courses_indexs = [self.get_course_index(course_code) for course_code in courses_codes]

        courses_indexs.sort()
        courses = [self.get_course_info(course_index) for course_index in courses_indexs]

        for i, course in enumerate(courses):
            object.__setattr__(course, "code", courses_codes[i])

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
